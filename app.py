import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_sock import Sock  # <-- Add this for plain WebSocket support
from face_service.embeddings import FaceEngine
from face_service.db import init_db, save_embedding, get_embeddings
import numpy as np
import logging
import json
import base64
import io

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'biosso-secret'

# Socket.IO for frontend browser clients
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Plain WebSocket for Java clients
sock = Sock(app)

engine = FaceEngine()
db_session = init_db()

# -------------------------
# REST ENDPOINTS
# -------------------------

@app.route("/register", methods=["POST"])
def register_user():
    """Receive image, extract embedding, save to DB"""
    
    file = request.files.get("image")
    user_id = request.form.get("user_id")

    if not file or not user_id:
        print("❌ Missing image or user_id")
        return jsonify({"error": "Missing image or user_id"}), 400

    try:
        embedding = engine.get_embedding(file.read())
        save_embedding(db_session, user_id, embedding)
        print(f"✅ Registered user {user_id}")
        return jsonify({"message": "Embedding registered", "user_id": user_id}), 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/verify", methods=["POST"])
def verify_user():
    """Receive image and compare with stored embeddings"""
    file = request.files.get("image")
    user_id = request.form.get("user_id")

    if not file or not user_id:
        return jsonify({"error": "Missing image or user_id"}), 400

    embedding = engine.get_embedding(file.read())
    stored = get_embeddings(db_session, user_id)

    if not stored:
        return jsonify({"error": "User not registered"}), 404

    sims = [engine.cosine_similarity(embedding, e) for e in stored]
    best = max(sims)
    success = best > 0.6

    return jsonify({"success": success, "similarity": float(best)}), 200


# -------------------------
# WEBSOCKET FOR JAVA CLIENT (Plain WebSocket)
# -------------------------
@sock.route('/ws')
def websocket_java(ws):
    """Plain WebSocket endpoint for Java client"""
    print("✅ Java WebSocket connected")
    
    try:
        while True:
            message = ws.receive()
            if message is None:
                break
                
            # Parse JSON message from Java
            try:
                data = json.loads(message)
                
                if data.get("type") == "image":
                    # Decode Base64 image
                    image_data = base64.b64decode(data["payload"])
                    user_id = data.get("userId", "unknown")
                    mode = data.get("mode", "login")
                    step = data.get("step", "0")
                    
                    print(f"📸 Received image from Java: {len(image_data)} bytes, user: '{user_id}', mode: {mode}, step: {step}")
                    
                    # Process with face engine
                    embedding = engine.get_embedding(image_data)
                    
                    if mode == "login":
                        # Get stored embeddings and compare
                        stored = get_embeddings(db_session, user_id)
                        
                        if stored:
                            sims = [engine.cosine_similarity(embedding, e) for e in stored]
                            best_similarity = max(sims)
                            success = best_similarity > 0.6
                            
                            response = {
                                "type": "result",
                                "status": "verified" if success else "rejected",
                                "similarity": float(best_similarity),
                                "user_id": user_id
                            }
                            print(f"✅ Login verification: {response['status']} (similarity: {best_similarity:.2f})")
                        else:
                            response = {
                                "type": "result",
                                "status": "rejected",
                                "message": "User not found",
                                "user_id": user_id
                            }
                            print(f"❌ User not registered: {user_id}")
                    
                    elif mode == "register":
                        # For registration, save the embedding
                        save_embedding(db_session, user_id, embedding)
                        response = {
                            "type": "result",
                            "status": "registered",
                            "user_id": user_id,
                            "message": "Image captured"
                        }
                        print(f"✅ Registration image captured for {user_id}")
                    
                    else:
                        response = {
                            "type": "result",
                            "status": "error",
                            "message": "Unknown mode"
                        }
                    
                    ws.send(json.dumps(response))
                    print(f"✅ Sent response: {response}")
                
                elif data.get("type") == "register":
                    # Full registration with user data and images
                    user_id = data.get("userId", "unknown")
                    images_b64 = data.get("images", [])
                    user_data = data.get("userData", {})
                    
                    print(f"👤 Received registration data for user: {user_id}")
                    print(f"   - Email: {user_data.get('email')}")
                    print(f"   - Name: {user_data.get('firstName')} {user_data.get('lastName')}")
                    print(f"   - Images: {len(images_b64)}")
                    
                    try:
                        # Check if user already exists
                        stored = get_embeddings(db_session, user_id)
                        if stored:
                            response = {
                                "type": "registration_result",
                                "status": "error",
                                "message": "User already registered",
                                "user_id": user_id
                            }
                            print(f"❌ User already exists: {user_id}")
                        else:
                            # Process all images and extract embeddings
                            embeddings = []
                            for i, image_b64 in enumerate(images_b64):
                                image_data = base64.b64decode(image_b64)
                                embedding = engine.get_embedding(image_data)
                                embeddings.append(embedding)
                                save_embedding(db_session, user_id, embedding)
                            
                            response = {
                                "type": "registration_result",
                                "status": "success",
                                "message": f"User registered with {len(embeddings)} face embeddings",
                                "user_id": user_id
                            }
                            print(f"✅ User registered successfully: {user_id} ({len(embeddings)} embeddings)")
                    
                    except Exception as e:
                        response = {
                            "type": "registration_result",
                            "status": "error",
                            "message": str(e),
                            "user_id": user_id
                        }
                        print(f"❌ Registration error: {e}")
                    
                    ws.send(json.dumps(response))
                
            except json.JSONDecodeError:
                # Handle binary data (if Java sends raw bytes)
                print(f"📸 Received binary data: {len(message)} bytes")
                # You can handle raw binary here if needed
                
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    finally:
        print("❌ Java WebSocket disconnected")


# -------------------------
# SOCKET.IO FOR FRONTEND (Browser clients)
# -------------------------
@socketio.on('connect')
def handle_socketio_connect():
    print("✅ Socket.IO connected (browser)")
    emit('message', {'status': 'connected'})


@socketio.on('frame')
def handle_frame(data):
    """Receive live frame from frontend for UX feedback"""
    feedback = engine.detect_quality(data)
    emit('feedback', {'message': feedback})


# -------------------------
# ENTRYPOINT
# -------------------------
if __name__ == "__main__":
    print("🚀 Starting bio-face service on port 5001...")
    print("   - REST API: http://0.0.0.0:5001")
    print("   - WebSocket (Java): ws://0.0.0.0:5001/ws")
    print("   - Socket.IO (Browser): ws://0.0.0.0:5001/socket.io/")
    socketio.run(app, host="0.0.0.0", port=5001, debug=True)
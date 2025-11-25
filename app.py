import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from face_service.embeddings import FaceEngine
from face_service.db import init_db, save_embedding, get_embeddings
import numpy as np
import logging
logging.basicConfig(level=logging.DEBUG)


app = Flask(__name__)
app.config['SECRET_KEY'] = 'biosso-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

engine = FaceEngine()
db_session = init_db()

# -------------------------
# REST ENDPOINTS
# -------------------------

@app.route("/register", methods=["POST"])
def register_user():
    """Receive image, extract embedding, save to DB"""

    # Log headers
    print("===== HEADERS =====")
    for key, value in request.headers.items():
        print(f"{key}: {value}")

    # Log content type
    print("\n===== CONTENT TYPE =====")
    print(request.content_type)

    # Log form fields
    print("\n===== FORM DATA =====")
    for key, value in request.form.items():
        print(f"{key}: {value}")

    # Log files
    print("\n===== FILES =====")
    for key, f in request.files.items():
        print(f"{key}: filename={f.filename}, content_type={f.content_type}, size={len(f.read())} bytes")
        f.seek(0)  # reset file pointer after reading

    # Log raw body (be careful with large files)
    print("\n===== RAW BODY PREVIEW (first 500 bytes) =====")
    raw_data = request.get_data()
    print(raw_data[:500])

    # Extract data
    file = request.files.get("image")
    user_id = request.form.get("user_id")

    if not file or not user_id:
        print("❌ Missing image or user_id")
        return jsonify({"error": "Missing image or user_id"}), 400

    # Example: process file
    # embedding = engine.get_embedding(file.read())
    # save_embedding(db_session, user_id, embedding)

    return jsonify({"message": "Embedding registered"}), 200


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
# WEBSOCKET (np. streaming / feedback UX)
# -------------------------
@socketio.on('connect')
def handle_connect():
    print("✅ WebSocket connected")
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
    socketio.run(app, host="0.0.0.0", port=5001, debug=True)


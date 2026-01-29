# import asyncio
# import websockets
# import json
# import base64
# import io
# from PIL import Image
# import random

# async def handle_connection(websocket):
#     print("✅ Java connected")

#     try:
#         async for message in websocket:
#             data = json.loads(message)

#             if data["type"] == "image":
#                 # Decode Base64 -> Image
#                 image_data = base64.b64decode(data["payload"])
#                 image = Image.open(io.BytesIO(image_data))
#                 image.save("received.jpg")

#                 print(f"📸 Received image: {len(image_data)} bytes")

#                 # Simulate AI processing
#                 await asyncio.sleep(1)
#                 response = {
#                     "type": "result",
#                     "status": "processed",
#                     "confidence": round(random.uniform(0.8, 0.99), 2)
#                 }
#                 await websocket.send(json.dumps(response))

#     except websockets.ConnectionClosed:
#         print("❌ Java disconnected")

# async def main():
#     print("🚀 Flask WebSocket server listening on ws://localhost:5001")
#     async with websockets.serve(handle_connection, "0.0.0.0", 5001):
#         await asyncio.Future()  # run forever

# if __name__ == "__main__":
#     asyncio.run(main())

import cv2
import numpy as np
import onnxruntime as ort

class FaceEngine:
    def __init__(self):
        # Path to pre-downloaded model inside container
        model_path = "/root/.insightface/models/buffalo_sc/w600k_mbf.onnx"
        self.session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])

    def preprocess_face(self, img):
        img = cv2.resize(img, (112, 112))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32)
        img = (img - 127.5) / 128.0
        img = np.transpose(img, [2, 0, 1])  # HWC -> CHW
        img = np.expand_dims(img, 0)        # Add batch dimension
        return img

    def get_embedding(self, img_bytes):
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Invalid image")

        # Run ONNX model
        x = self.preprocess_face(img)
        inputs = {self.session.get_inputs()[0].name: x}
        embedding = self.session.run(None, inputs)[0][0]
        return embedding.tolist()

    def cosine_similarity(self, a, b):
        a, b = np.array(a), np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def detect_quality(self, frame_bytes):
        """Simple feedback: detect if face is present"""
        np_arr = np.frombuffer(frame_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return "Invalid frame"
        # Optional: naive detection (e.g., using OpenCV Haar or MTCNN)
        # For now, just check if any face-like region is visible (dummy)
        h, w = img.shape[:2]
        if h < 50 or w < 50:
            return "Frame too small"
        return "Frame received"

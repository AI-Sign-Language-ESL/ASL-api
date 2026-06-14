class MockProvider:
    """
    Mock AI Provider that returns hardcoded predictions
    for sign language recognition.
    """
    def predict_sign(self, video_path: str) -> dict:
        # Simulate processing time or return directly
        return {
            "prediction": "HELLO",
            "confidence": 0.95
        }

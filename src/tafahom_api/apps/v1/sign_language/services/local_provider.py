class LocalModelProvider:
    """
    Local AI Provider for the upcoming CV model.
    The AI team will provide model.pth, labels.json, and inference.py.
    """
    def __init__(self):
        # TODO: Load model.pth and labels.json here later
        pass

    def predict_sign(self, video_path: str) -> dict:
        # TODO: Integrate with inference.py when provided
        raise NotImplementedError("Local AI model is not ready yet.")

import logging
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

class ModalPredictionClient:
    """
    Service responsible for calling the Modal Sign Language API.
    """
    
    def __init__(self):
        self.predict_url = getattr(settings, 'MODAL_API_PREDICT_URL', "https://zein1312004--sign-language-api-predict.modal.run")
        self.health_url = getattr(settings, 'MODAL_API_HEALTH_URL', "https://zein1312004--sign-language-api-health.modal.run")
        self.timeout = getattr(settings, 'MODAL_API_TIMEOUT', 15.0)

    def check_health(self) -> bool:
        """Check if the Modal API is healthy."""
        try:
            response = httpx.get(self.health_url, timeout=5.0)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Modal API health check failed: {e}")
            return False

    def predict(self, sequence: list) -> dict:
        """
        Send a sequence of shape (96, 27, 3) to the Modal API.
        
        Expected request body:
        { "sequence": [[[x,y,z], ...]] }
        
        Returns:
        { "prediction": "اب", "confidence": 0.6178 }
        """
        # Request validation
        if not sequence or not isinstance(sequence, list):
            raise ValueError("Sequence must be a non-empty list.")
        
        if len(sequence) != 96:
            raise ValueError(f"Sequence length must be exactly 96 frames. Got {len(sequence)}.")
        
        if len(sequence[0]) != 27:
            raise ValueError(f"Each frame must contain exactly 27 landmarks. Got {len(sequence[0])}.")

        import numpy as np

        # Validate and log sequence statistics
        arr = np.array(sequence, dtype=np.float32)
        shape = arr.shape
        nonzero = int(np.count_nonzero(arr))
        mean = float(np.mean(arr))
        std = float(np.std(arr))

        logger.info(
            f"REST Predict sequence validation: shape={shape}, nonzero={nonzero}, mean={mean:.4f}, std={std:.4f}"
        )

        # Hands check: Left hand [7:17], Right hand [17:27]
        left_hand = arr[:, 7:17, :]
        right_hand = arr[:, 17:27, :]
        has_left = np.any(left_hand != 0, axis=(1, 2))
        has_right = np.any(right_hand != 0, axis=(1, 2))
        has_hand = has_left | has_right
        frames_with_hands = int(np.sum(has_hand))

        # Check validation thresholds:
        # 1. No hands detected for most frames (less than 48 of the 96 frames)
        # 2. Non-zero count below 3000
        # 3. Low movement / static sequence (std < 0.05)
        if frames_with_hands < 48 or nonzero < 3000 or std < 0.05:
            logger.warning(
                f"REST Sequence rejected by validation: frames_with_hands={frames_with_hands}/96, nonzero={nonzero}, std={std:.4f}"
            )
            return {
                "prediction": "NO_SIGN",
                "confidence": 0.0
            }

        try:
            payload = {"sequence": sequence}
            
            response = httpx.post(
                self.predict_url,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            if "prediction" not in data or "confidence" not in data:
                raise ValueError(f"Unexpected Modal API response format: {data}")
                
            return {
                "prediction": data["prediction"],
                "confidence": float(data["confidence"])
            }
            
        except httpx.TimeoutException:
            logger.error("Modal API prediction timed out.")
            raise TimeoutError("Prediction request to Modal API timed out.")
        except httpx.HTTPStatusError as e:
            logger.error(f"Modal API prediction returned HTTP error: {e}")
            raise RuntimeError(f"Modal API prediction failed with status {e.response.status_code}")
        except Exception as e:
            logger.error(f"Modal API prediction failed: {e}")
            raise

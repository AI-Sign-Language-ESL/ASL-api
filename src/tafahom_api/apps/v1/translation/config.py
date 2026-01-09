from django.conf import settings

# =============================================================================
# STREAMING / PIPELINE LIMITS
# =============================================================================
SEND_INTERVAL = 5
MAX_BUFFER_SIZE = 120
MAX_BATCH_FRAMES = 30

MAX_FRAMES_PER_REQUEST = 64
MAX_REQUESTS_PER_SESSION = 5
PIPELINE_TIMEOUT_SECONDS = 15

HEARTBEAT_TIMEOUT = 30

WS_MAX_MESSAGES_PER_SECOND = getattr(
    settings, "WS_MAX_MESSAGES_PER_SECOND", 30
)

WS_MAX_CONNECTION_TIME = getattr(
    settings, "WS_MAX_CONNECTION_TIME", 60 * 15
)

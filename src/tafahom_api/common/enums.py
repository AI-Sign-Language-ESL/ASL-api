from django.utils.translation import gettext_lazy as _

# =========================
# TRANSLATION
# =========================

TRANSLATION_DIRECTIONS = [
    ("to_sign", _("To Sign Language")),
    ("from_sign", _("From Sign Language")),
]

TRANSLATION_STATUS = [
    ("pending", _("Pending")),
    ("processing", _("Processing")),
    ("completed", _("Completed")),
    ("failed", _("Failed")),
]

PROCESSING_MODES = [
    ("standard", _("Standard")),
    ("realtime", _("Realtime")),
]

INPUT_TYPES = [
    ("text", _("Text")),
    ("voice", _("Voice")),
    ("video", _("Video")),
]

OUTPUT_TYPES = [
    ("avatar", _("3D Avatar")),
    ("video", _("Video")),
    ("text", _("Text")),
    ("voice", _("Voice")),
]

# =========================
# LANGUAGES
# =========================

SPOKEN_LANGUAGES = [
    ("en-US", _("English (US)")),
    ("ar-EG", _("Arabic (Egypt)")),
]

LANGUAGE_CODES = [
    ("en", _("English")),
    ("ar", _("Arabic")),
]

TEXT_DIRECTIONS = [
    ("ltr", _("Left to Right")),
    ("rtl", _("Right to Left")),
]

SIGN_LANGUAGES = [
    ("ase", _("American Sign Language")),
    ("egs", _("Egyptian Sign Language")),
]

# =========================
# DATASET (🔐 HARDENED)
# =========================

DATASET_CONTRIBUTION_STATUS = [
    ("pending", _("Pending Review")),
    ("processing", _("Processing")),
    ("approved", _("Approved")),
    ("rejected", _("Rejected")),
    ("failed", _("Failed")),
]

# =========================
# BILLING
# =========================

SUBSCRIPTION_STATUS = [
    ("active", _("Active")),
    ("cancelled", _("Cancelled")),
    ("expired", _("Expired")),
]

PLAN_TYPES = [
    ("free", _("Free")),
    ("basic", _("Basic")),
    ("premium", _("Premium")),
]

CREDIT_TRANSACTION_TYPES = [
    ("used", _("Used")),
    ("earned", _("Earned")),
]



# ✅ FIX: Added "approved" to pending so Admin can approve immediately
DATASET_STATUS_TRANSITIONS = {
    "pending": {"processing", "rejected", "approved"}, 
    "processing": {"approved", "rejected", "failed"},
    "approved": set(), # Final state
    "rejected": {"pending"}, # Allow retry/re-review if needed
    "failed": {"pending"},
}
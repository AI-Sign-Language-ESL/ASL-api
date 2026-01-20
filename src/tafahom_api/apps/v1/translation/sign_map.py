# sign_map.py

SIGN_MAP = {
    # Emergency
    "اسعاف": "ambulance.mov",
    "نجده": "emergency.mov",
    "شرطه": "police.mov",
    # Accidents & danger
    "حادث": "accident.mov",
    "حريق": "fire.mov",
    "خطر": "danger.mov",
    # Utilities
    "كهربا": "power_cut.mov",
    "قطع": "power_cut.mov",
    # Problems
    "مشكله": "big_problem.mov",
    # Network
    "شبكه": "no_signal.mov",
    "مفيش": "no_signal.mov",
}

# 🔁 NLP → Dataset normalization
SYNONYM_MAP = {
    "حرائق": "حريق",
    "نار": "حريق",
    "حريقه": "حريق",
    "إسعاف": "اسعاف",
    "سياره": "حادث",
    "حادثه": "حادث",
    "كبيره": "مشكله",
    "مشاكل": "مشكله",
    "لا": None,
    "فقط": None,
    "وصول": None,
}

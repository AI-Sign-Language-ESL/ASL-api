class LanguageService:
    @staticmethod
    def get(current_language="en"):
        return {
            "current_language": current_language,
            "languages": [
                {
                    "code": "en",
                    "name": "English",
                    "native_name": "English",
                    "direction": "ltr",
                    "flag": "🇺🇸",
                    "is_default": True,
                },
                {
                    "code": "ar",
                    "name": "Arabic",
                    "native_name": "العربية",
                    "direction": "rtl",
                    "flag": "🇪🇬",
                    "is_default": False,
                },
            ],
        }

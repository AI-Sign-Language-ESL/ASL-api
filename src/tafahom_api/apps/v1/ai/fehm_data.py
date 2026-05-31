"""
Predefined questions, answers, actions, and subscription rules for Fehm.
"""

WELCOME_EN = (
    "👋 Hello, I'm Fehm.\n\n"
    "Your Tafahom assistant for learning, communication, and accessibility.\n\n"
    "I'm here to help you discover platform features, continue your learning "
    "journey, answer questions, and assist you throughout Tafahom.\n\n"
    "How would you like me to help you today?"
)

WELCOME_AR = (
    "👋 مرحباً، أنا فهم.\n\n"
    "مساعدك الذكي في منصة تفاهم للتعلم والتواصل وسهولة الوصول.\n\n"
    "أنا هنا لمساعدتك في اكتشاف ميزات المنصة، متابعة رحلة التعلم، "
    "الإجابة على أسئلتك، والاستفادة من خدمات تفاهم.\n\n"
    "كيف يمكنني مساعدتك اليوم؟"
)

WELCOME_QUICK_ACTIONS = [
    {"label": "What is Tafahom?", "type": "question", "key": "what_is_tafahom"},
    {"label": "What can you do?", "type": "question", "key": "what_can_you_do"},
    {"label": "Show Lessons", "type": "action", "key": "show_lessons"},
    {"label": "Continue Learning", "type": "action", "key": "continue_learning"},
    {"label": "Open Translator", "type": "action", "key": "open_translator"},
    {"label": "Contact Support", "type": "question", "key": "contact_support"},
]

QA = {
    "who_are_you": {
        "en": "Hello! I am Fehm (فهم), Tafahom's virtual assistant. "
              "I help users navigate the platform, discover features, "
              "learn sign language, and access Tafahom services.",
        "ar": "مرحباً! أنا فهم، مساعد تفاهم الافتراضي. "
              "أساعد المستخدمين في التنقل في المنصة، اكتشاف الميزات، "
              "تعلم لغة الإشارة، والوصول إلى خدمات تفاهم.",
    },
    "what_is_tafahom": {
        "en": "Tafahom is a platform focused on accessibility, sign language "
              "communication, learning experiences, translation tools, "
              "and collaborative communication.",
        "ar": "تفاهم هي منصة تركز على سهولة الوصول، التواصل بلغة الإشارة، "
              "تجارب التعلم، أدوات الترجمة، والتواصل التعاوني.",
    },
    "what_can_you_do": {
        "en": "I can help you:\n\n"
              "• Explain Tafahom features\n"
              "• Guide you through sign language learning\n"
              "• Help you find lessons\n"
              "• Open platform features\n"
              "• Assist with meetings\n"
              "• Explain subscription plans\n"
              "• Answer frequently asked questions",
        "ar": "يمكنني مساعدتك:\n\n"
              "• شرح ميزات تفاهم\n"
              "• إرشادك خلال تعلم لغة الإشارة\n"
              "• مساعدتك في العثور على الدروس\n"
              "• فتح ميزات المنصة\n"
              "• المساعدة في الاجتماعات\n"
              "• شرح خطط الاشتراك\n"
              "• الإجابة على الأسئلة الشائعة",
    },
    "plans": {
        "en": "Tafahom currently offers:\n\n"
              "• Free\n"
              "• Basic\n"
              "• Go\n"
              "• Enterprise",
        "ar": "تفاهم تقدم حالياً:\n\n"
              "• مجاني\n"
              "• أساسي\n"
              "• انطلق\n"
              "• مؤسسات",
    },
    "how_to_learn": {
        "en": "You can access lessons, practice exercises, educational content, "
              "and guided learning experiences through Tafahom.",
        "ar": "يمكنك الوصول إلى الدروس وتمارين التدريب والمحتوى التعليمي "
              "وتجارب التعلم الموجهة من خلال تفاهم.",
    },
    "contact_support": {
        "en": "Please visit the Support section within Tafahom. "
              "You can also describe your issue and I will try to help.",
        "ar": "يرجى زيارة قسم الدعم داخل تفاهم. يمكنك أيضاً وصف مشكلتك وسأحاول المساعدة.",
    },
    "help": {
        "en": "You can ask me:\n\n"
              "• What is Tafahom?\n"
              "• What can you do?\n"
              "• Show lessons\n"
              "• Continue learning\n"
              "• Open translator\n"
              "• Join meeting\n"
              "• Contact support",
        "ar": "يمكنك أن تسألني:\n\n"
              "• ما هي تفاهم؟\n"
              "• ماذا يمكنك أن تفعل؟\n"
              "• عرض الدروس\n"
              "• متابعة التعلم\n"
              "• فتح المترجم\n"
              "• الانضمام إلى اجتماع\n"
              "• الاتصال بالدعم",
    },
}

# Intent matching patterns (question → key mapping)
INTENT_PATTERNS = {
    "who_are_you": [
        "who are you", "what are you", "你是谁", "tell me about yourself",
        "من انت", "من أنت", "عرفني بنفسك",
    ],
    "what_is_tafahom": [
        "what is tafahom", "what's tafahom", "tell me about tafahom",
        "ما هي تفاهم", "ما تفاهم", "اخبرني عن تفاهم", "عرفني عن تفاهم",
    ],
    "what_can_you_do": [
        "what can you do", "what do you do", "your features", "capabilities",
        "ماذا يمكنك ان تفعل", "ماذا تفعل", "ما هي قدراتك", "الميزات",
    ],
    "plans": [
        "plans", "subscription", "pricing", "what plans", "available plans",
        "خطط", "الاشتراك", "الأسعار", "ما هي الخطط", "الخطط المتاحة",
    ],
    "how_to_learn": [
        "how to learn", "learn sign language", "start learning", "lessons",
        "كيف اتعلم", "تعلم لغة الإشارة", "بدء التعلم", "الدروس",
    ],
    "contact_support": [
        "contact support", "support", "help me", "customer service",
        "اتصل بالدعم", "الدعم", "ساعدني", "خدمة العملاء",
    ],
    "help": [
        "help", "what can i ask", "commands",
        "مساعدة", "ماذا يمكنني ان اسأل", "الأوامر",
    ],
}

# Actions — matched by keywords, mapped to structured responses
ACTIONS = {
    "show_lessons": {
        "patterns": [
            "show lessons", "view lessons", "lessons list", "all lessons",
            "عرض الدروس", "الدروس", "قائمة الدروس",
        ],
        "response": {
            "type": "navigate",
            "destination": "lessons",
            "message_en": "Opening lessons page...",
            "message_ar": "جاري فتح صفحة الدروس...",
        },
    },
    "continue_learning": {
        "patterns": [
            "continue learning", "resume", "my course", "continue",
            "متابعة التعلم", "استئناف", "دورتي", "متابعة",
        ],
        "response": {
            "type": "navigate",
            "destination": "learning",
            "message_en": "Taking you to your learning dashboard...",
            "message_ar": "جاري نقلك إلى لوحة التعلم...",
        },
    },
    "open_translator": {
        "patterns": [
            "open translator", "translator", "translate", "translation tool",
            "فتح المترجم", "مترجم", "ترجمة", "أداة الترجمة",
        ],
        "response": {
            "type": "navigate",
            "destination": "translator",
            "message_en": "Opening translator...",
            "message_ar": "جاري فتح المترجم...",
        },
    },
    "show_profile": {
        "patterns": [
            "show profile", "my profile", "profile", "account",
            "عرض الملف الشخصي", "ملفي", "الملف الشخصي", "الحساب",
        ],
        "response": {
            "type": "navigate",
            "destination": "profile",
            "message_en": "Opening your profile...",
            "message_ar": "جاري فتح ملفك الشخصي...",
        },
    },
    "open_settings": {
        "patterns": [
            "open settings", "settings", "preferences",
            "فتح الإعدادات", "إعدادات", "التفضيلات",
        ],
        "response": {
            "type": "navigate",
            "destination": "settings",
            "message_en": "Opening settings...",
            "message_ar": "جاري فتح الإعدادات...",
        },
    },
    "join_meeting": {
        "patterns": [
            "join meeting", "join a meeting", "meeting invite",
            "الانضمام إلى اجتماع", "انضم إلى اجتماع", "دعوة اجتماع",
        ],
        "min_plan": "free",
        "response": {
            "type": "navigate",
            "destination": "meetings/join",
            "message_en": "Opening meeting join page...",
            "message_ar": "جاري فتح صفحة الانضمام إلى الاجتماع...",
        },
    },
    "create_meeting": {
        "patterns": [
            "create meeting", "start meeting", "new meeting", "schedule meeting",
            "إنشاء اجتماع", "بدء اجتماع", "اجتماع جديد", "جدولة اجتماع",
        ],
        "min_plan": "enterprise",
        "response": {
            "type": "meeting_created",
            "message_en": "Meeting created successfully",
            "message_ar": "تم إنشاء الاجتماع بنجاح",
            "actions": [
                {"label": "Join Meeting", "type": "join_meeting"},
            ],
        },
    },
    "meeting_history": {
        "patterns": [
            "meeting history", "past meetings", "my meetings", "show meetings",
            "سجل الاجتماعات", "الاجتماعات السابقة", "اجتماعاتي", "عرض الاجتماعات",
        ],
        "min_plan": "enterprise",
        "response": {
            "type": "navigate",
            "destination": "meetings/history",
            "message_en": "Opening meeting history...",
            "message_ar": "جاري فتح سجل الاجتماعات...",
        },
    },
}

PLAN_RANK = {
    "free": 0,
    "basic": 1,
    "go": 2,
    "enterprise": 3,
}

import re
import logging
from tafahom_api.apps.v1.translation.sign_map import SYNONYM_MAP

logger = logging.getLogger(__name__)

def normalize_arabic(text: str) -> str:
    """
    Strict Arabic text normalization.
    - Standardizes Alef/Hamza to bare Alef.
    - Standardizes Teh Marbuta to Heh.
    - Standardizes Yeh variants to standard Yeh.
    - Standardizes Waw variants.
    - Removes Tashkeel and Tatweel.
    - Removes punctuation and standardizes whitespace.
    - Normalizes family and relationship terms by stripping possessive suffixes.
    """
    if not text:
        return ""
        
    # Remove Tashkeel and Tatweel
    text = re.sub(r'[\u064B-\u065F\u0640]', '', text)
    
    # Standardize Alef and Hamza variants to bare Alef 'ا'
    text = re.sub(r'[أإآٱء]', 'ا', text)
    
    # Standardize Teh Marbuta 'ة' to Heh 'ه'
    text = re.sub(r'ة', 'ه', text)
    
    # Standardize Yeh variants 'ى' 'ئ' to 'ي'
    text = re.sub(r'[ىئ]', 'ي', text)
    
    # Standardize Waw variants 'ؤ' to 'و'
    text = re.sub(r'ؤ', 'و', text)
    
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Family and relationship term normalization
    irregular_map = {
        "صديقي": "اصدقاء",
        "اصدقائي": "اصدقاء", "اصدقائهم": "اصدقاء", "اصدقائنا": "اصدقاء",
        "زميلي": "زملاء",
        "زملائي": "زملاء", "زملاهم": "زملاء", "زملائنا": "زملاء",
    }
    
    stems_to_canonical = {
        "ام": "ام",
        "ابو": "اب",
        "اب": "اب",
        "اخو": "اخ",
        "اخ": "اخ",
        "اخت": "اخت",
        "عم": "عم",
        "عمت": "عمه",
        "عمه": "عمه",
        "خال": "خال",
        "خالت": "خاله",
        "خاله": "خاله",
        "جار": "جار"
    }
    
    # Suffixes after letter normalization
    suffixes = ["يا", "ي", "ها", "هم", "هن", "نا", "كم", "ك", "و", "ه"]
    
    words = text.split()
    normalized_words = []
    
    for word in words:
        if word in irregular_map:
            normalized_words.append(irregular_map[word])
            continue
            
        # Preserve canonical bases to avoid destroying dictionary mappings (e.g. عمه, خاله)
        if word in stems_to_canonical.values():
            normalized_words.append(word)
            continue
            
        matched = False
        for stem, canonical in stems_to_canonical.items():
            for suffix in suffixes:
                if word == stem + suffix:
                    normalized_words.append(canonical)
                    matched = True
                    break
            if matched:
                break
                
        if not matched:
            normalized_words.append(word)
            
    return " ".join(normalized_words)

def apply_synonyms(text: str) -> str:
    """
    Applies synonym replacements. Must be called AFTER text is normalized
    (assuming SYNONYM_MAP keys are also normalized in memory).
    """
    if not text:
        return ""
        
    # We must replace longest synonyms first to avoid partial overlap bugs
    sorted_synonyms = sorted(SYNONYM_MAP.keys(), key=lambda k: len(k.split()), reverse=True)
    
    for syn in sorted_synonyms:
        if syn in text:
            target = SYNONYM_MAP[syn]
            if target:  # Target might be None (e.g. stop words)
                # Word boundary replacement
                text = re.sub(rf'\b{syn}\b', target, text)
            else:
                # Remove stop words
                text = re.sub(rf'\b{syn}\b', '', text)
                
    return re.sub(r'\s+', ' ', text).strip()

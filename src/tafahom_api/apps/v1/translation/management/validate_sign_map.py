import sys
import os
import json
from collections import defaultdict

# Add directory to pythonpath so imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from collections import defaultdict
import json
from tafahom_api.apps.v1.translation.sign_map import ANIMATION_MAP, SIGN_MAP, SYNONYM_MAP
from tafahom_api.apps.v1.translation.services.normalization import normalize_arabic

def validate_maps():
    report = {
        "conflicts": [],
        "synonym_errors": [],
        "total_animations": len(ANIMATION_MAP),
        "total_signs": len(SIGN_MAP),
        "total_synonyms": len(SYNONYM_MAP)
    }

    # 1. Check for conflicts after normalization
    normalized_anims = defaultdict(list)
    for phrase, anim in ANIMATION_MAP.items():
        norm = normalize_arabic(phrase)
        if norm:
            normalized_anims[norm].append({"original": phrase, "anim": anim})

    for norm, entries in normalized_anims.items():
        if len(entries) > 1:
            # Check if they point to different animations
            anims = set(e["anim"] for e in entries)
            if len(anims) > 1:
                report["conflicts"].append({
                    "normalized_phrase": norm,
                    "entries": entries
                })

    # 2. Check Synonym targets
    for syn, target in SYNONYM_MAP.items():
        if target is None:
            continue
        # Does the target exist in ANY map after normalization?
        # Because in our new system, target strings from SYNONYM_MAP will be substituted into text,
        # then we normalize text and do Trie lookup. So the target itself doesn't HAVE to be an exact key,
        # it just needs to not be a dead end. But it's good practice for targets to be valid keys.
        norm_target = normalize_arabic(target)
        found = False
        if norm_target in normalized_anims:
            found = True
        
        # Check SIGN_MAP
        for sign_phrase in SIGN_MAP.keys():
            if normalize_arabic(sign_phrase) == norm_target:
                found = True
                break
                
        if not found:
            # If the target is multiple words, it might match a combination in the trie, but let's warn
            report["synonym_errors"].append({
                "synonym": syn,
                "target": target,
                "normalized_target": norm_target,
                "error": "Target does not exist in ANIMATION_MAP or SIGN_MAP"
            })

    return report

if __name__ == "__main__":
    report = validate_maps()
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'validation_report.json'))
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Validation complete. Report saved to {output_path}")
    print(f"Found {len(report['conflicts'])} conflicts and {len(report['synonym_errors'])} synonym errors.")

from sign_map import ANIMATION_MAP

unique_words = {}

for word, animation in ANIMATION_MAP.items():
    if animation not in unique_words:
        unique_words[animation] = word

result = list(unique_words.values())

print(f"Unique signs: {len(result)}")
for word in sorted(result):
    print(word)
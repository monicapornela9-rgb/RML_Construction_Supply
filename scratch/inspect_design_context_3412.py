import json
import re

path = r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3412\output.txt'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"Output size: {len(content)} characters")

# Check if screenshot is returned
screenshots = re.findall(r'https?://[^\s"]+(?:png|jpg|webp)[^\s"]*', content)
print("Image URLs found:", len(screenshots))
for u in screenshots[:10]:
    print("  ", u)

# Check structure of the output
print("\n--- First 1500 chars ---")
print(content[:1500])

import re

with open(r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3179\output.txt', 'r', encoding='utf-8') as f:
    text = f.read()

labels = re.findall(r'<frame id="([^"]+)" name="Label"[^>]*>\s*<text id="([^"]+)" name="([^"]+)"', text)
print(f"Total labels found: {len(labels)}")
unique_labels = sorted(list(set(l[2].strip() for l in labels)))
for ul in unique_labels:
    if any(k in ul.lower() for k in ['name', 'phone', 'address', 'password', 'email', 'company']):
        print(f"  {ul}")

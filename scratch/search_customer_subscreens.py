import re

path = r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3179\output.txt'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

keywords = ['dashboard', 'profile', 'setting', 'notification', 'order list', 'my order']

matches = []
for m in re.finditer(r'<frame id="([^"]+)" name="([^"]+)"[^>]*width="([^"]+)"[^>]*height="([^"]+)"', text):
    fid, name, w, h = m.group(1), m.group(2), m.group(3), m.group(4)
    for kw in keywords:
        if kw in name.lower() and float(w) >= 800:
            matches.append((fid, name, w, h))
            break

print(f"Total matching screens: {len(matches)}")
for m in matches:
    print(f"  [{m[0]}] {m[1]} ({m[2]}x{m[3]})")

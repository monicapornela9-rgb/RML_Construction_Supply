import re

with open(r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3205\output.txt', 'r', encoding='utf-8') as f:
    text = f.read()

sections = re.findall(r'<section id="([^"]+)" name="([^"]+)"', text)
frames = re.findall(r'<frame id="([^"]+)" name="([^"]+)"', text)

print("=== SECTIONS in Page 1 ===")
for s in sections:
    print(f"{s[0]}: {s[1]}")

print(f"\nTotal frames found: {len(frames)}")
print("\n=== MATCHING FRAMES in Page 1 ===")
keywords = ['register', 'registration', 'sign up', 'signup', 'account', 'create', 'onboard', 'join', 'auth', 'sign-in', 'login']
for fid, fname in frames:
    if any(k in fname.lower() for k in keywords):
        print(f"{fid}: {fname}")

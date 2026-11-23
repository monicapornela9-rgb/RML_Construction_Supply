import re

steps = [(3179, "FINAL DRAFT UI/UX"), (3197, "Page 1"), (3205, "High fidelity · Manager & Driver")]

for step, pname in steps:
    path = rf'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\{step}\output.txt'
    with open(path, 'r', encoding='utf-8') as f:
        t = f.read()
    fs = re.findall(r'<frame id="([^"]+)" name="([^"]+)"', t)
    print(f"=== {pname} (Total frames: {len(fs)}) ===")
    matches = []
    for fid, fn in fs:
        if any(w in fn.lower() for w in ['register', 'registration', 'sign up', 'signup', 'create account', 'new account']):
            matches.append((fid, fn))
    print(f"Matches: {len(matches)}")
    for fid, fn in matches:
        print(f"  {fid}: {fn}")

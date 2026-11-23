import re

steps = [(3179, "FINAL DRAFT UI/UX"), (3197, "Page 1"), (3205, "High fidelity · Manager & Driver")]

keywords = ['landing', 'home', 'main', 'index', 'customer', 'store', 'shop', 'web', 'overview', 'front']

for step, pname in steps:
    path = rf'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\{step}\output.txt'
    try:
        with open(path, 'r', encoding='utf-8') as f:
            t = f.read()
    except Exception as e:
        print(f"Error reading {step}: {e}")
        continue
    fs = re.findall(r'<frame id="([^"]+)" name="([^"]+)"', t)
    print(f"=== {pname} (Total frames: {len(fs)}) ===")
    matches = []
    for fid, fn in fs:
        for kw in keywords:
            if kw in fn.lower():
                matches.append((fid, fn))
                break
    for fid, fn in matches:
        print(f"  {fid}: {fn}")

import re

steps = [(3179, "FINAL DRAFT UI/UX"), (3197, "Page 1"), (3205, "High fidelity · Manager & Driver")]

for step, pname in steps:
    path = rf'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\{step}\output.txt'
    with open(path, 'r', encoding='utf-8') as f:
        t = f.read()
    
    # In get_design_context or XML tree, let's look for top-level frame patterns
    # Top-level frames are usually direct children of <document> or have no parent frame or are large (width > 1000)
    # Let's find tags like <frame id="..." name="..." ... width="..." height="...">
    matches = re.findall(r'<frame id="([^"]+)" name="([^"]+)"[^>]*width="([^"]+)"[^>]*height="([^"]+)"', t)
    print(f"\n==================== {pname} ====================")
    top_frames = []
    for fid, name, w, h in matches:
        try:
            fw = float(w)
            fh = float(h)
            if fw >= 1000 and fh >= 600:
                top_frames.append((fid, name, fw, fh))
        except:
            pass
    print(f"Large screens found: {len(top_frames)}")
    for fid, name, fw, fh in top_frames:
        print(f"  [{fid}] {name} ({int(fw)}x{int(fh)})")

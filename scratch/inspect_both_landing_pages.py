import re

path = r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3179\output.txt'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

def print_frame_children(frame_id, depth=0, max_depth=3):
    pattern = rf'<(frame|section) id="{frame_id}" name="([^"]+)"[^>]*width="([^"]+)"[^>]*height="([^"]+)"'
    m = re.search(pattern, text)
    if not m:
        print("Frame not found:", frame_id)
        return
    tag, name, w, h = m.group(1), m.group(2), m.group(3), m.group(4)
    print(f"ROOT: [{frame_id}] {name} ({tag}, {w}x{h})")
    
    # Let's find all direct or near-direct child frames inside this frame
    # We can do this by searching between start pos of frame_id and end of frame_id or next top frame
    start_pos = m.start()
    # Find matching closing tag or next large frame
    # Since XML might be huge, let's scan lines starting after start_pos
    snippet = text[start_pos:start_pos+30000]
    lines = snippet.split('\n')
    base_indent = len(lines[0]) - len(lines[0].lstrip())
    
    for l in lines[1:]:
        if not l.strip():
            continue
        indent = len(l) - len(l.lstrip())
        rel_indent = (indent - base_indent) // 2
        if rel_indent <= 0 and ('<frame ' in l or '<section ' in l):
            break
        if rel_indent <= max_depth:
            # check if it has name
            nm = re.search(r'<(frame|text|component|instance|rectangle|vector|section) id="([^"]+)" name="([^"]+)"', l)
            if nm:
                elem, eid, ename = nm.group(1), nm.group(2), nm.group(3)
                print(f"{'  ' * rel_indent}[{eid}] <{elem}> {ename}")

print("==================== Frame 172:12907 (Landing Page RML 1 — High fidelity) ====================")
print_frame_children('172:12907', max_depth=3)

print("\n==================== Frame 186:57 (Landing page · Hi-Fi · Rubber Gloves) ====================")
print_frame_children('186:57', max_depth=3)

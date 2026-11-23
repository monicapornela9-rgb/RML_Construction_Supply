import re

steps = [(3179, "FINAL DRAFT UI/UX"), (3197, "Page 1"), (3205, "High fidelity · Manager & Driver")]

for step, pname in steps:
    path = rf'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\{step}\output.txt'
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"\n==================== {pname} ====================")
    # Let's inspect sections and top level frames (indentation level 2 spaces or 4 spaces)
    for line in lines:
        if line.startswith('  <section ') or line.startswith('    <frame ') or line.startswith('  <frame '):
            m = re.search(r'id="([^"]+)" name="([^"]+)"', line)
            if m:
                print(f"  {line[:10].strip()} {m.group(1)}: {m.group(2)}")

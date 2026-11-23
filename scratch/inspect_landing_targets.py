import re

path = r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3179\output.txt'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

target_ids = ['172:12904', '172:12906', '184:99', '186:57']

for tid in target_ids:
    print(f"\n==================== Target ID {tid} ====================")
    # Find the tag start
    pattern = rf'<(section|frame) id="{tid}" name="([^"]+)"'
    m = re.search(pattern, text)
    if m:
        tag_type = m.group(1)
        name = m.group(2)
        print(f"Found {tag_type} {tid}: {name}")
        # Let's extract the snippet following this tag
        start_pos = m.start()
        # Find next 3000 chars or lines
        snippet = text[start_pos:start_pos+4000]
        # print child frames/sections
        child_lines = [l for l in snippet.split('\n')[:35]]
        for l in child_lines:
            print(l)
    else:
        print(f"Target {tid} not found directly with regex")

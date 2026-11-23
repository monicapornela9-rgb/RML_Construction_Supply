import re

path = r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3484\output.txt'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

m = re.search(r'<frame id="172:1470" name="Main"', text)
if m:
    start_pos = m.start()
    snippet = text[start_pos:start_pos+15000]
    lines = snippet.split('\n')
    for l in lines[:70]:
        print(l)

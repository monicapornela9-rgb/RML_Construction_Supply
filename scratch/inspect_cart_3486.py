import re

path = r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3486\output.txt'
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

# Let's inspect snippet after Aside or in Main
m = re.search(r'data-name="Main"', code)
if not m:
    m = re.search(r'<main', code)
start = m.start() if m else 0
print(code[start:start+4000])

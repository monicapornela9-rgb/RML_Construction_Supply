import re

path = r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3179\output.txt'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for line in lines:
    if line.startswith('  <section ') or line.startswith('  <frame '):
        print(line.strip())

import re

path = r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3486\output.txt'
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

# Let's search for "My shopping cart"
pos = code.find("My shopping cart")
print(code[pos-200:pos+3500])

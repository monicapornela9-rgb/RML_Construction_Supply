import re

path = r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3412\output.txt'
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

# Let's write out the clean code to a text file for easy reading
out_path = r'C:\xampp\htdocs\RML_Construction_Supply\scratch\figma_landing_code.jsx'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(code)

print(f"Written {len(code)} characters to {out_path}")

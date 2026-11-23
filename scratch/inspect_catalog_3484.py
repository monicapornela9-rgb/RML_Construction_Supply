import re

path = r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3484\output.txt'
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

# Let's inspect data-name elements
data_names = re.findall(r'data-name="([^"]+)"', code)
print(f"Total elements: {len(data_names)}")
for dn in data_names[:40]:
    print("  *", dn)

# Print first 2000 characters
print("\n--- Code snippet ---")
print(code[:2000])

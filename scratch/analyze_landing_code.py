import re

path = r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3412\output.txt'
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

# Let's find all data-name elements in the code
elements = re.findall(r'data-name="([^"]+)"', code)
print(f"Total elements with data-name: {len(elements)}")
for e in elements[:60]:
    print(" -", e)

# Let's save a nicely formatted text breakdown of the sections
sections = re.findall(r'<div[^>]*data-name="([^"]+)"[^>]*>(.*?)(?=<div[^>]*data-name=|$)', code, re.DOTALL)
print("\nTop-level sections found:")
for name, content in sections:
    if name in ["Navigation", "Hero", "Shop by category", "About RML", "How ordering works", "Service areas", "Customer access", "Customer feedback", "Footer"]:
        print(f"\n==================== Section: {name} ====================")
        # extract text contents inside this section
        texts = re.findall(r'>([^<]+)<', content)
        clean_texts = [t.strip() for t in texts if t.strip() and not t.strip().startswith('{') and not t.strip().startswith('const')]
        for ct in clean_texts[:15]:
            print("  *", ct)

import re

with open(r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3179\output.txt', 'r', encoding='utf-8') as f:
    text = f.read()

texts = re.findall(r'<text id="([^"]+)" name="([^"]+)"', text)
print(f"Total texts found in 172:35: {len(texts)}")

keywords = ['register', 'registration', 'sign up', 'signup', 'create an account', 'create account', 'don\'t have an account', 'new customer']
matches = []
for tid, tname in texts:
    if any(k in tname.lower() for k in keywords):
        matches.append((tid, tname))

print(f"Found {len(matches)} matching texts:")
for tid, tname in matches[:50]:
    print(f"{tid}: {tname}")

import re

def inspect_file(step_num, title):
    path = rf'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\{step_num}\output.txt'
    with open(path, 'r', encoding='utf-8') as f:
        t = f.read()
    print(f"\n==================== STEP {step_num}: {title} ====================")
    texts = re.findall(r'>([^<]+)<', t)
    clean_texts = [x.strip() for x in texts if x.strip() and not x.strip().startswith('{') and not x.strip().startswith('const') and not x.strip().startswith('import')]
    seen = set()
    first_texts = []
    for ct in clean_texts:
        if ct not in seen:
            seen.add(ct)
            first_texts.append(ct)
            if len(first_texts) >= 40:
                break
    for ct in first_texts:
        print("  -", ct)

inspect_file(3486, "Cart")
inspect_file(3488, "Checkout")
inspect_file(3490, "Payment Selection")
inspect_file(3492, "Tracking")
inspect_file(3494, "Support")

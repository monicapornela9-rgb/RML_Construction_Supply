import re
import os

steps = [
    (3484, "Customer Product Catalog — Hi-Fi"),
    (3486, "Customer Shopping cart — High fidelity"),
    (3488, "Customer Checkout"),
    (3490, "Customer Payment Method Selection"),
    (3492, "Customer Order Tracking"),
    (3494, "Customer Support"),
    (3496, "Customer Product details · Steel Bar")
]

for step_num, title in steps:
    path = rf'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\{step_num}\output.txt'
    if not os.path.exists(path):
        print(f"File not found: {path}")
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"\n==================================================")
    print(f"STEP {step_num}: {title} (Length: {len(content)})")
    print(f"==================================================")
    
    # Extract asset URLs
    assets = re.findall(r'const (img\w+) = `\${assetPathPrefix}/([^`]+)`;', content)
    if assets:
        print("Assets:")
        for varname, fname in assets:
            print(f"  {varname} -> {fname}")
            
    # Extract top-level elements and text snippets
    data_names = re.findall(r'data-name="([^"]+)"', content)
    print("Key layout elements (data-name):")
    for dn in data_names[:25]:
        print(f"  - {dn}")

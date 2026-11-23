import sys, os
sys.path.insert(0, os.getcwd())
from scratch.catalog_data import OFFICIAL_CATALOG

with open('scratch/extracted_doc.txt', 'r', encoding='utf-8') as f:
    raw_lines = f.readlines()

catalog_prices = {}
for p in OFFICIAL_CATALOG:
    if p["variations"]:
        for v in p["variations"]:
            catalog_prices[(p["name"].lower(), v["name"].lower())] = v["price"]
    else:
        catalog_prices[(p["name"].lower(), "")] = p["price"]

print(f"Total catalog pricing entries: {len(catalog_prices)}")

doc_entries = []
for line in raw_lines:
    line = line.strip()
    if '=' in line and not line.startswith('---'):
        doc_entries.append(line)

print(f"Total doc lines with '=': {len(doc_entries)}")
for e in doc_entries:
    print("  ", e)

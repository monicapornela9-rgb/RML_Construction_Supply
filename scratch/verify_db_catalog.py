import os, sys, sqlite3

PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "RML")
sys.path.insert(0, PROJECT_DIR)

from catalog_data import OFFICIAL_CATALOG

conn = sqlite3.connect(os.path.join(PROJECT_DIR, "rml_database.db"))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== VERIFYING DATABASE CATALOG AGAINST OFFICIAL DOCX CATALOG ===")

total_prods = 0
total_vars = 0
total_skus = 0
mismatches = []

for p in OFFICIAL_CATALOG:
    total_prods += 1
    p_name = p["name"].strip()
    db_p = cur.execute("SELECT * FROM products WHERE LOWER(name) = LOWER(?) AND is_active = 1", (p_name,)).fetchone()
    if not db_p:
        mismatches.append(f"Missing Product in DB: {p_name}")
        continue

    variations = p.get("variations", [])
    if variations:
        for v in variations:
            total_vars += 1
            total_skus += 1
            v_name = v["name"].strip()
            v_price = float(v["price"])
            db_v = cur.execute("SELECT * FROM product_variations WHERE product_id = ? AND LOWER(variation_name) = LOWER(?)", (db_p["id"], v_name)).fetchone()
            if not db_v:
                mismatches.append(f"Missing Variation for {p_name}: {v_name}")
            elif float(db_v["price"]) != v_price:
                mismatches.append(f"Price Mismatch for {p_name} ({v_name}): doc={v_price}, db={db_v['price']}")
    else:
        total_skus += 1
        expected_price = float(p["price"])
        if float(db_p["price"]) != expected_price:
            mismatches.append(f"Price Mismatch for standalone {p_name}: doc={expected_price}, db={db_p['price']}")

print(f"Total Parent Products in Catalog: {total_prods}")
print(f"Total Variations in Catalog: {total_vars}")
print(f"Total Purchasable SKUs: {total_skus}")
print(f"Total Discrepancies/Mismatches: {len(mismatches)}")

if mismatches:
    for m in mismatches:
        print("  [ERROR]", m)
else:
    print(" 100% PERFECT MATCH! Every single product, variation, and price in DB matches the official document exactly!")

# Check Categories breakdown
print("\n--- Breakdown by Category ---")
cats = cur.execute("""
    SELECT c.name, COUNT(DISTINCT p.id) as prod_count, COUNT(v.id) as var_count
    FROM categories c
    JOIN products p ON c.id = p.category_id AND p.is_active = 1
    LEFT JOIN product_variations v ON p.id = v.product_id AND v.is_available = 1
    GROUP BY c.id
    ORDER BY c.id
""").fetchall()

for c in cats:
    print(f"  * {c['name']}: {c['prod_count']} products, {c['var_count']} variations")

conn.close()

import sys, os, sqlite3
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from scratch.catalog_data import OFFICIAL_CATALOG

DB_PATH = os.path.join(BASE_DIR, "RML", "rml_database.db")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. Create product_variations table if not exists
cur.execute("""
CREATE TABLE IF NOT EXISTS product_variations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    variation_name TEXT NOT NULL,
    price REAL NOT NULL,
    unit TEXT,
    stock_quantity INTEGER NOT NULL DEFAULT 50,
    is_available INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
""")

# 2. Add columns if missing
prod_cols = [r[1] for r in cur.execute("PRAGMA table_info(products)").fetchall()]
if "is_active" not in prod_cols:
    cur.execute("ALTER TABLE products ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1;")

oi_cols = [r[1] for r in cur.execute("PRAGMA table_info(order_items)").fetchall()]
if "variation_id" not in oi_cols:
    cur.execute("ALTER TABLE order_items ADD COLUMN variation_id INTEGER;")
if "variation_name" not in oi_cols:
    cur.execute("ALTER TABLE order_items ADD COLUMN variation_name TEXT;")

# 3. Ensure categories
cats = [
    ("Paints & Thinners", "Paints, thinners, varnishes, and wood preservatives"),
    ("Lighting & Fixtures", "LED bulbs, fluorescent tubes, fixtures, and electrical boxes"),
    ("Adhesives & Sealants", "Contact cement, silicones, gap fillers, and pipe cements"),
    ("Tapes, Wires & Fasteners", "Electrical tapes, masking tapes, tie wire, and teflon"),
    ("Cement & Aggregates", "Cement, sand, gravel, and bulk filling aggregates"),
    ("Boards & Lumber", "Plywood, shena boards, and framing sheets"),
    ("Steel & Rebar", "Deformed steel bars, plain sheets, yero, and welding rods"),
    ("Plumbing & Fittings", "Neltex PVC pipes, bio pipes, elbows, tees, wyes, cleanouts, and fittings"),
    ("Tools, Hardware & Safety", "Hinges, brushes, blades, safety helmets, gloves, and bibcock faucets"),
]
for cat_name, cat_desc in cats:
    cur.execute("INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)", (cat_name, cat_desc))

cat_map = {r["name"]: r["id"] for r in cur.execute("SELECT id, name FROM categories").fetchall()}

# Deactivate legacy products that are not part of the official catalog
official_names = {p["name"].strip().lower() for p in OFFICIAL_CATALOG}
cur.execute("UPDATE products SET is_active = 0")

imported_products = 0
imported_variations = 0

for p_data in OFFICIAL_CATALOG:
    cid = cat_map[p_data["category"]]
    p_name = p_data["name"].strip()
    p_desc = p_data["description"].strip()
    p_unit = p_data["unit"].strip()
    p_img = p_data.get("image_url", "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500")

    variations = p_data.get("variations", [])
    if variations:
        base_price = min(v["price"] for v in variations)
        total_stock = sum(50 for _ in variations)
    else:
        base_price = p_data["price"]
        total_stock = 50

    # Check if product with this exact name already exists
    existing = cur.execute("SELECT id FROM products WHERE LOWER(name) = LOWER(?)", (p_name,)).fetchone()
    if existing:
        pid = existing["id"]
        cur.execute("""
            UPDATE products
            SET category_id = ?, description = ?, unit = ?, price = ?,
                image_url = ?, is_active = 1, stock_quantity = MAX(stock_quantity, ?)
            WHERE id = ?
        """, (cid, p_desc, p_unit, base_price, p_img, total_stock, pid))
    else:
        cur.execute("""
            INSERT INTO products (category_id, name, description, unit, price, stock_quantity, low_stock_threshold, image_url, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 20, ?, 1)
        """, (cid, p_name, p_desc, p_unit, base_price, total_stock, p_img))
        pid = cur.lastrowid

    imported_products += 1

    # Insert / update variations
    for v in variations:
        v_name = v["name"].strip()
        v_price = float(v["price"])
        v_unit = v.get("unit", p_unit).strip()

        v_exist = cur.execute("SELECT id FROM product_variations WHERE product_id = ? AND LOWER(variation_name) = LOWER(?)", (pid, v_name)).fetchone()
        if v_exist:
            cur.execute("""
                UPDATE product_variations
                SET price = ?, unit = ?, is_available = 1
                WHERE id = ?
            """, (v_price, v_unit, v_exist["id"]))
        else:
            cur.execute("""
                INSERT INTO product_variations (product_id, variation_name, price, unit, stock_quantity, is_available)
                VALUES (?, ?, ?, ?, 50, 1)
            """, (pid, v_name, v_price, v_unit))
        imported_variations += 1

conn.commit()
print(f"IMPORT COMPLETE:")
print(f"Total Active Official Products: {imported_products}")
print(f"Total Imported Variations: {imported_variations}")
print(f"Total Purchasable Options: {imported_products - len([p for p in OFFICIAL_CATALOG if p['variations']]) + imported_variations}")

# Verify integrity
active_prods = cur.execute("SELECT COUNT(*) FROM products WHERE is_active = 1").fetchone()[0]
total_vars = cur.execute("SELECT COUNT(*) FROM product_variations WHERE is_available = 1").fetchone()[0]
print(f"DB Active Products: {active_prods}, DB Active Variations: {total_vars}")

conn.close()

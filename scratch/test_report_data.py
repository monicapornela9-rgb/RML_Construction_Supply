import sqlite3

conn = sqlite3.connect('RML/rml_database.db')
conn.row_factory = sqlite3.Row

cat_sales = conn.execute('''
    SELECT c.name, COALESCE(SUM(oi.subtotal), 0) AS revenue
    FROM categories c
    LEFT JOIN products p ON c.id = p.category_id
    LEFT JOIN order_items oi ON p.id = oi.product_id
    LEFT JOIN orders o ON oi.order_id = o.id AND o.order_status != 'rejected'
    GROUP BY c.id
    ORDER BY revenue DESC
''').fetchall()

print("=== Category Sales ===")
for c in cat_sales:
    print(f"Category: {c['name']} | Revenue: {c['revenue']}")

daily_orders = conn.execute('''
    SELECT date(created_at) AS order_date, COUNT(*) AS count,
           SUM(CASE WHEN order_status IN ('approved', 'in_transit', 'delivered') THEN 1 ELSE 0 END) AS approved_count
    FROM orders
    GROUP BY date(created_at)
    ORDER BY order_date DESC
    LIMIT 7
''').fetchall()

print("\n=== Daily Orders ===")
for d in daily_orders:
    print(f"Date: {d['order_date']} | Count: {d['count']} | Approved: {d['approved_count']}")

conn.close()

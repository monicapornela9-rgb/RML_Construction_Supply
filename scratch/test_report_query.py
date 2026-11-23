import sqlite3

conn = sqlite3.connect('RML/rml_database.db')
conn.row_factory = sqlite3.Row

def test_queries(start_date, end_date):
    cat_query = """
        SELECT c.name, COALESCE(SUM(oi.subtotal), 0) AS revenue
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id
        LEFT JOIN order_items oi ON p.id = oi.product_id
        LEFT JOIN orders o ON oi.order_id = o.id AND o.order_status != 'rejected'
    """
    cat_params = []
    if start_date:
        cat_query += " AND date(o.created_at) >= date(?)"
        cat_params.append(start_date)
    if end_date:
        cat_query += " AND date(o.created_at) <= date(?)"
        cat_params.append(end_date)
    cat_query += " GROUP BY c.id ORDER BY revenue DESC"
    cat_sales = conn.execute(cat_query, cat_params).fetchall()

    daily_query = """
        SELECT date(created_at) AS order_date, COUNT(*) AS count,
               SUM(CASE WHEN order_status IN ('approved', 'in_transit', 'delivered') THEN 1 ELSE 0 END) AS approved_count
        FROM orders
        WHERE 1=1
    """
    daily_params = []
    if start_date:
        daily_query += " AND date(created_at) >= date(?)"
        daily_params.append(start_date)
    if end_date:
        daily_query += " AND date(created_at) <= date(?)"
        daily_params.append(end_date)
    daily_query += " GROUP BY date(created_at) ORDER BY order_date DESC LIMIT 7"
    daily_orders = list(reversed(conn.execute(daily_query, daily_params).fetchall()))

    max_cat_rev = max([float(c["revenue"] or 0) for c in cat_sales] or [1.0])
    if max_cat_rev <= 0:
        max_cat_rev = 1.0

    max_daily_count = max([int(d["count"] or 0) for d in daily_orders] or [1])
    if max_daily_count <= 0:
        max_daily_count = 1

    print(f"Test start='{start_date}', end='{end_date}':")
    print(f"  max_cat_rev: {max_cat_rev}, max_daily_count: {max_daily_count}")
    print(f"  daily dates: {[d['order_date'] for d in daily_orders]}")
    print(f"  daily counts: {[d['count'] for d in daily_orders]}")

test_queries("", "")
test_queries("2026-11-01", "2026-11-30")
test_queries("2025-01-01", "2025-01-02")
conn.close()

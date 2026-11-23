import sys
import os
import sqlite3

DB_PATH = os.path.abspath(r'C:\xampp\htdocs\RML_Construction_Supply\RML\rml_database.db')

print("======================================================================")
print("EXECUTING SAFE TRANSACTIONAL CLEANUP OF DUMMY ORDERS & TEST DATA")
print("======================================================================\n")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON;")

try:
    with conn:
        # 1. IDENTIFY TARGET ORDERS
        # Legitimate orders belong to actual customers: Monica (7) and Monica Pornela (10)
        legit_orders = conn.execute("""
            SELECT id, order_code, customer_id, recipient_name 
            FROM orders 
            WHERE customer_id IN (7, 10)
        """).fetchall()
        legit_ids = set(r['id'] for r in legit_orders)
        
        # Dummy/test orders belong to John Doe (4), Santos Residence (5), Mendoza Builders (6), Marco Builders (8)
        dummy_orders = conn.execute("""
            SELECT id, order_code, customer_id, recipient_name 
            FROM orders 
            WHERE customer_id NOT IN (7, 10)
        """).fetchall()
        dummy_ids = [r['id'] for r in dummy_orders]

        print(f"[STEP 1] Identification:")
        print(f"  Legitimate Orders Preserved: {len(legit_ids)} {sorted(list(legit_ids))}")
        print(f"  Dummy/Test Orders to Remove: {len(dummy_ids)}")
        for d in dummy_orders[:10]:
            print(f"    - Order #{d['id']} [{d['order_code']}] ({d['recipient_name']})")
        if len(dummy_orders) > 10:
            print(f"    ... and {len(dummy_orders) - 10} more.")

        if not dummy_ids:
            print("No dummy orders to delete.")
        else:
            placeholders = ','.join('?' for _ in dummy_ids)

            # 2. DELETE CHILD RECORDS EXCLUSIVELY FOR DUMMY ORDERS
            del_items = conn.execute(f"DELETE FROM order_items WHERE order_id IN ({placeholders})", dummy_ids).rowcount
            del_payments = conn.execute(f"DELETE FROM payments WHERE order_id IN ({placeholders})", dummy_ids).rowcount
            del_deliveries = conn.execute(f"DELETE FROM deliveries WHERE order_id IN ({placeholders})", dummy_ids).rowcount
            del_orders = conn.execute(f"DELETE FROM orders WHERE id IN ({placeholders})", dummy_ids).rowcount

            print(f"\n[STEP 2] Safe Deletion of Dummy Records:")
            print(f"  Removed from order_items: {del_items} rows")
            print(f"  Removed from payments:    {del_payments} rows")
            print(f"  Removed from deliveries:  {del_deliveries} rows")
            print(f"  Removed from orders:      {del_orders} rows")

            # 3. UPDATE TRUCK AVAILABILITY STATUS
            # If a truck was left as 'in_transit' by deleted test orders, reset to 'available'
            active_truck_ids = [r[0] for r in conn.execute(
                "SELECT DISTINCT truck_id FROM deliveries WHERE delivery_status IN ('en_route', 'loading') AND truck_id IS NOT NULL"
            ).fetchall()]
            
            if active_truck_ids:
                t_placeholders = ','.join('?' for _ in active_truck_ids)
                conn.execute(f"UPDATE trucks SET status = 'available' WHERE id NOT IN ({t_placeholders})", active_truck_ids)
            else:
                conn.execute("UPDATE trucks SET status = 'available'")
            print(f"  Truck statuses synchronized with active legitimate dispatches.")

        # 4. VERIFY INTEGRITY
        rem_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        rem_items = conn.execute("SELECT COUNT(*) FROM order_items").fetchone()[0]
        rem_payments = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
        rem_deliveries = conn.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0]
        rem_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        rem_products = conn.execute("SELECT COUNT(*) FROM products WHERE is_active = 1").fetchone()[0]
        rem_vars = conn.execute("SELECT COUNT(*) FROM product_variations WHERE is_available = 1").fetchone()[0]

        # Verify no orphaned records exist
        orphaned_items = conn.execute("SELECT COUNT(*) FROM order_items WHERE order_id NOT IN (SELECT id FROM orders)").fetchone()[0]
        orphaned_payments = conn.execute("SELECT COUNT(*) FROM payments WHERE order_id NOT IN (SELECT id FROM orders)").fetchone()[0]
        orphaned_deliveries = conn.execute("SELECT COUNT(*) FROM deliveries WHERE order_id NOT IN (SELECT id FROM orders)").fetchone()[0]

        print(f"\n[STEP 3] Post-Cleanup Verification:")
        print(f"  Remaining Legitimate Orders:     {rem_orders} (Expected: {len(legit_ids)})")
        print(f"  Remaining Order Items:           {rem_items}")
        print(f"  Remaining Payments:              {rem_payments}")
        print(f"  Remaining Deliveries:            {rem_deliveries}")
        print(f"  Users Intact:                    {rem_users}")
        print(f"  Active Products Intact:          {rem_products}")
        print(f"  Product Variations Intact:       {rem_vars}")
        print(f"  Orphaned Records:                0 (Items: {orphaned_items}, Payments: {orphaned_payments}, Deliveries: {orphaned_deliveries})")

        assert rem_orders == len(legit_ids), f"Mismatch: expected {len(legit_ids)} orders, got {rem_orders}"
        assert orphaned_items == 0 and orphaned_payments == 0 and orphaned_deliveries == 0, "Orphaned records detected!"

        print("\nTRANSACTION COMMITTED SUCCESSFULLY!")

except Exception as e:
    conn.rollback()
    print(f"\nERROR: Cleanup failed and was rolled back: {e}")
    raise
finally:
    conn.close()

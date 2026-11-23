import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rml_database.db")


def get_db():
    """Return a SQLite3 connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


CATALOG_PRODUCTS = []


def seed_catalog(cur):
    """Seed official product catalog and variations extracted from rml.docx."""
    try:
        from RML.catalog_data import OFFICIAL_CATALOG
    except ImportError:
        from catalog_data import OFFICIAL_CATALOG

    new_categories = [
        ("Paints & Thinners", "Paints, thinners, varnishes, and wood preservatives"),
        ("Lighting & Fixtures", "LED bulbs, fluorescent tubes, fixtures, and enclosures"),
        ("Adhesives & Sealants", "Contact cement, silicones, gap fillers, and pipe cements"),
        ("Tapes, Wires & Fasteners", "Electrical tapes, masking tapes, tie wire, and teflon"),
        ("Cement & Aggregates", "Cement, sand, gravel, and bulk filling aggregates"),
        ("Boards & Lumber", "Plywood, shena boards, and framing sheets"),
        ("Steel & Rebar", "Deformed steel bars, plain sheets, yero, and welding rods"),
        ("Plumbing & Fittings", "Neltex PVC pipes, bio pipes, elbows, tees, wyes, cleanouts, and fittings"),
        ("Tools, Hardware & Safety", "Hinges, brushes, blades, safety helmets, gloves, and bibcock faucets"),
    ]
    for cat_name, cat_desc in new_categories:
        cur.execute("INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)", (cat_name, cat_desc))

    cat_map = {row[1]: row[0] for row in cur.execute("SELECT id, name FROM categories").fetchall()}

    # Mark legacy products not in official catalog as inactive (preserving existing order references)
    cur.execute("UPDATE products SET is_active = 0")

    for p_data in OFFICIAL_CATALOG:
        cid = cat_map.get(p_data["category"])
        if not cid:
            continue
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

        existing = cur.execute("SELECT id FROM products WHERE LOWER(name) = LOWER(?)", (p_name,)).fetchone()
        if existing:
            pid = existing[0]
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

        for v in variations:
            v_name = v["name"].strip()
            v_price = float(v["price"])
            v_unit = v.get("unit", p_unit).strip()

            v_exist = cur.execute(
                "SELECT id FROM product_variations WHERE product_id = ? AND LOWER(variation_name) = LOWER(?)",
                (pid, v_name)
            ).fetchone()
            if v_exist:
                cur.execute("""
                    UPDATE product_variations
                    SET price = ?, unit = ?, is_available = 1
                    WHERE id = ?
                """, (v_price, v_unit, v_exist[0]))
            else:
                cur.execute("""
                    INSERT INTO product_variations (product_id, variation_name, price, unit, stock_quantity, is_available)
                    VALUES (?, ?, ?, ?, 50, 1)
                """, (pid, v_name, v_price, v_unit))


def init_db():
    """Create tables if they do not exist, run migrations, and seed sample data."""
    conn = get_db()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id TEXT UNIQUE,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            address TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'customer', 'driver', 'staff')),
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            unit TEXT NOT NULL,
            price REAL NOT NULL,
            stock_quantity INTEGER NOT NULL DEFAULT 0,
            low_stock_threshold INTEGER NOT NULL DEFAULT 20,
            image_url TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

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

        CREATE TABLE IF NOT EXISTS inventory_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL CHECK(movement_type IN ('stock_in', 'stock_out', 'adjustment')),
            quantity INTEGER NOT NULL,
            remarks TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS trucks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            truck_code TEXT NOT NULL UNIQUE,
            plate_number TEXT NOT NULL UNIQUE,
            capacity TEXT,
            status TEXT NOT NULL DEFAULT 'available' CHECK(status IN ('available', 'in_transit', 'maintenance'))
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code TEXT NOT NULL UNIQUE,
            customer_id INTEGER NOT NULL,
            recipient_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            delivery_address TEXT NOT NULL,
            preferred_date TEXT,
            delivery_slot TEXT,
            special_instructions TEXT,
            subtotal REAL NOT NULL DEFAULT 0,
            delivery_fee REAL NOT NULL DEFAULT 1500,
            vat_amount REAL NOT NULL DEFAULT 0,
            total_amount REAL NOT NULL DEFAULT 0,
            order_status TEXT NOT NULL DEFAULT 'pending_scheduling'
                CHECK(order_status IN ('pending', 'pending_scheduling', 'for_scheduling', 'awaiting_confirmation', 'schedule_confirmed', 'pending_payment', 'pending_payment_verification', 'payment_verified', 'ready_for_dispatch', 'scheduled', 'payment_pending', 'out_for_delivery', 'delivered', 'cancelled', 'approved', 'rejected', 'payment_rejected', 'preparing', 'in_transit')),
            assigned_date TEXT,
            assigned_time_slot TEXT,
            schedule_confirmed_at TEXT,
            schedule_status TEXT NOT NULL DEFAULT 'unassigned',
            rejection_reason TEXT,
            approval_notes TEXT,
            authorized_by INTEGER,
            authorized_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (customer_id) REFERENCES users(id),
            FOREIGN KEY (authorized_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL UNIQUE,
            method TEXT NOT NULL CHECK(method IN ('cash', 'qr')),
            reference_number TEXT,
            receipt_note TEXT,
            payer_name TEXT,
            bank_used TEXT,
            proof_file TEXT,
            amount REAL NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'pending'
                CHECK(payment_status IN ('pending', 'pending_verification', 'verified', 'rejected', 'payment_due', 'unpaid', 'paid')),
            paid_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            verified_by INTEGER,
            verified_at TEXT,
            rejection_reason TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (verified_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_code TEXT NOT NULL UNIQUE,
            order_id INTEGER NOT NULL UNIQUE,
            driver_id INTEGER,
            truck_id INTEGER,
            delivery_window TEXT,
            delivery_status TEXT NOT NULL DEFAULT 'queued'
                CHECK(delivery_status IN ('queued', 'assigned', 'authorized', 'ready_for_dispatch', 'loading', 'en_route', 'delivered', 'cancelled')),
            current_lat REAL DEFAULT 13.9411,
            current_lng REAL DEFAULT 121.1631,
            last_gps_update TEXT,
            recipient_received_by TEXT,
            recipient_role TEXT,
            delivery_notes TEXT,
            quantity_received TEXT,
            completion_time TEXT,
            recipient_acknowledged INTEGER DEFAULT 0,
            proof_file TEXT,
            delivered_at TEXT,
            authorized_by INTEGER,
            authorized_at TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (driver_id) REFERENCES users(id),
            FOREIGN KEY (truck_id) REFERENCES trucks(id),
            FOREIGN KEY (authorized_by) REFERENCES users(id)
        );
        """
    )

    # Migrations for existing tables if columns are missing
    table_migrations = [
        ("users", "reset_token", "TEXT"),
        ("users", "reset_token_expires_at", "TEXT"),
        ("users", "failed_login_attempts", "INTEGER DEFAULT 0"),
        ("users", "locked_until", "TEXT"),
        ("users", "is_verified", "INTEGER DEFAULT 1"),
        ("users", "verification_token", "TEXT"),
        ("products", "is_active", "INTEGER NOT NULL DEFAULT 1"),
        ("order_items", "variation_id", "INTEGER"),
        ("order_items", "variation_name", "TEXT"),
        ("orders", "approval_notes", "TEXT"),
        ("orders", "assigned_date", "TEXT"),
        ("orders", "assigned_time_slot", "TEXT"),
        ("orders", "schedule_confirmed_at", "TEXT"),
        ("orders", "schedule_status", "TEXT DEFAULT 'unassigned'"),
        ("orders", "authorized_by", "INTEGER"),
        ("orders", "authorized_at", "TEXT"),
        ("orders", "reservation_expires_at", "TEXT"),
        ("payments", "payer_name", "TEXT"),
        ("payments", "bank_used", "TEXT"),
        ("payments", "proof_file", "TEXT"),
        ("payments", "verified_by", "INTEGER"),
        ("payments", "verified_at", "TEXT"),
        ("payments", "rejection_reason", "TEXT"),
        ("deliveries", "quantity_received", "TEXT"),
        ("deliveries", "completion_time", "TEXT"),
        ("deliveries", "recipient_acknowledged", "INTEGER DEFAULT 0"),
        ("deliveries", "proof_file", "TEXT"),
        ("deliveries", "authorized_by", "INTEGER"),
        ("deliveries", "authorized_at", "TEXT"),
    ]
    for tbl, col, col_def in table_migrations:
        try:
            cols = [r[1] for r in cur.execute(f"PRAGMA table_info({tbl})").fetchall()]
            if col not in cols:
                cur.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_def}")
        except Exception:
            pass

    # Ensure delivery_availability table exists
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS delivery_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            max_capacity INTEGER NOT NULL DEFAULT 3,
            is_available INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            UNIQUE(delivery_date, time_slot)
        );
        """
    )

    # Ensure delivery_settings table exists
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS delivery_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL
        );
        """
    )

    # Ensure notifications table exists
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_id INTEGER,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            notification_type TEXT NOT NULL DEFAULT 'general',
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
        );
        """
    )

    # Ensure cart_items table exists
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            variation_id INTEGER,
            quantity INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY (variation_id) REFERENCES product_variations(id) ON DELETE CASCADE
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cart_items_user ON cart_items(user_id);")

    # Ensure access_logs table exists for access & role management audit
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            affected_user_id INTEGER,
            affected_user_name TEXT,
            affected_user_email TEXT,
            affected_user_role TEXT,
            performed_by INTEGER,
            performed_by_name TEXT,
            details TEXT,
            ip_address TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (affected_user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (performed_by) REFERENCES users(id) ON DELETE SET NULL
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_access_logs_created ON access_logs(created_at);")

    # Seed default delivery settings
    cur.executemany(
        "INSERT OR IGNORE INTO delivery_settings (setting_key, setting_value) VALUES (?, ?)",
        [
            ("reservation_timeout_hours", "24"),
            ("default_slot_capacity", "3"),
            ("lead_time_days", "1"),
            ("horizon_days", "14"),
        ],
    )

    # Seed delivery availability for next 14 days if table is empty
    avail_count = cur.execute("SELECT COUNT(*) FROM delivery_availability").fetchone()[0]
    if avail_count == 0:
        from datetime import datetime as dt, timedelta
        today_d = dt.now().date()
        std_slots = ["Morning (08:00 - 12:00)", "Afternoon (13:00 - 17:00)"]
        for i in range(1, 15):
            day_target = today_d + timedelta(days=i)
            day_str = day_target.strftime("%Y-%m-%d")
            # Sunday closed by default
            is_avail = 0 if day_target.weekday() == 6 else 1
            day_note = "Sunday - Closed" if day_target.weekday() == 6 else None
            for s_name in std_slots:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO delivery_availability (delivery_date, time_slot, max_capacity, is_available, notes)
                    VALUES (?, ?, 3, ?, ?)
                    """,
                    (day_str, s_name, is_avail, day_note),
                )

    # Update CHECK constraint on orders table to support payment verification & dispatch authorization statuses
    orders_sql = cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='orders'").fetchone()
    if orders_sql and "pending_review" not in orders_sql[0]:
        cur.executescript(
            """
            PRAGMA foreign_keys = OFF;
            DROP TABLE IF EXISTS orders_migrated;
            CREATE TABLE orders_migrated (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_code TEXT NOT NULL UNIQUE,
                customer_id INTEGER NOT NULL,
                recipient_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                delivery_address TEXT NOT NULL,
                preferred_date TEXT,
                delivery_slot TEXT,
                special_instructions TEXT,
                subtotal REAL NOT NULL DEFAULT 0,
                delivery_fee REAL NOT NULL DEFAULT 1500,
                vat_amount REAL NOT NULL DEFAULT 0,
                total_amount REAL NOT NULL DEFAULT 0,
                order_status TEXT NOT NULL DEFAULT 'pending_scheduling'
                    CHECK(order_status IN ('pending', 'pending_review', 'pending_scheduling', 'for_scheduling', 'awaiting_confirmation', 'schedule_confirmed', 'pending_payment', 'pending_payment_verification', 'payment_verified', 'ready_for_dispatch', 'scheduled', 'payment_pending', 'out_for_delivery', 'delivered', 'cancelled', 'approved', 'rejected', 'payment_rejected', 'preparing', 'in_transit')),
                assigned_date TEXT,
                assigned_time_slot TEXT,
                schedule_confirmed_at TEXT,
                schedule_status TEXT NOT NULL DEFAULT 'unassigned',
                rejection_reason TEXT,
                approval_notes TEXT,
                authorized_by INTEGER,
                authorized_at TEXT,
                reservation_expires_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (customer_id) REFERENCES users(id),
                FOREIGN KEY (authorized_by) REFERENCES users(id)
            );

            INSERT INTO orders_migrated (
                id, order_code, customer_id, recipient_name, phone, delivery_address,
                preferred_date, delivery_slot, special_instructions,
                subtotal, delivery_fee, vat_amount, total_amount, order_status,
                assigned_date, assigned_time_slot, schedule_confirmed_at, schedule_status,
                rejection_reason, approval_notes, authorized_by, authorized_at, reservation_expires_at, created_at
            )
            SELECT
                id, order_code, customer_id, recipient_name, phone, delivery_address,
                preferred_date, delivery_slot, special_instructions,
                subtotal, delivery_fee, vat_amount, total_amount, order_status,
                assigned_date, assigned_time_slot, schedule_confirmed_at,
                COALESCE(schedule_status, 'unassigned'),
                rejection_reason, approval_notes, authorized_by, authorized_at,
                reservation_expires_at, created_at
            FROM orders;

            DROP TABLE orders;
            ALTER TABLE orders_migrated RENAME TO orders;
            PRAGMA foreign_keys = ON;
            """
        )

    # Update CHECK constraint on payments table to support payment verification workflow
    payments_sql = cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='payments'").fetchone()
    if payments_sql and "payment_due" not in payments_sql[0]:
        cur.executescript(
            """
            PRAGMA foreign_keys = OFF;
            DROP TABLE IF EXISTS payments_migrated;
            CREATE TABLE payments_migrated (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL UNIQUE,
                method TEXT NOT NULL CHECK(method IN ('cash', 'qr')),
                reference_number TEXT,
                receipt_note TEXT,
                payer_name TEXT,
                bank_used TEXT,
                proof_file TEXT,
                amount REAL NOT NULL,
                payment_status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(payment_status IN ('pending', 'pending_verification', 'verified', 'rejected', 'payment_due', 'unpaid', 'paid')),
                paid_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                verified_by INTEGER,
                verified_at TEXT,
                rejection_reason TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (verified_by) REFERENCES users(id)
            );

            INSERT INTO payments_migrated (
                id, order_id, method, reference_number, receipt_note, payer_name, bank_used, proof_file, amount, payment_status, paid_at
            )
            SELECT
                id, order_id, method, reference_number, receipt_note, payer_name, bank_used, proof_file, amount, payment_status, paid_at
            FROM payments;

            DROP TABLE payments;
            ALTER TABLE payments_migrated RENAME TO payments;
            PRAGMA foreign_keys = ON;
            """
        )

    # Update CHECK constraint on deliveries table to support proposed, reserved, confirmed, authorized statuses
    deliveries_sql = cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='deliveries'").fetchone()
    if deliveries_sql and "'proposed'" not in deliveries_sql[0]:
        cur.executescript(
            """
            PRAGMA foreign_keys = OFF;
            DROP TABLE IF EXISTS deliveries_migrated;
            CREATE TABLE deliveries_migrated (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                delivery_code TEXT NOT NULL UNIQUE,
                order_id INTEGER NOT NULL UNIQUE,
                driver_id INTEGER,
                truck_id INTEGER,
                delivery_window TEXT,
                delivery_status TEXT NOT NULL DEFAULT 'queued'
                    CHECK(delivery_status IN ('pending_schedule', 'queued', 'assigned', 'proposed', 'reserved', 'confirmed', 'authorized', 'ready_for_dispatch', 'loading', 'en_route', 'delivered', 'cancelled')),
                current_lat REAL DEFAULT 13.9411,
                current_lng REAL DEFAULT 121.1631,
                last_gps_update TEXT,
                recipient_received_by TEXT,
                recipient_role TEXT,
                delivery_notes TEXT,
                quantity_received TEXT,
                completion_time TEXT,
                recipient_acknowledged INTEGER DEFAULT 0,
                proof_file TEXT,
                delivered_at TEXT,
                authorized_by INTEGER,
                authorized_at TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (driver_id) REFERENCES users(id),
                FOREIGN KEY (truck_id) REFERENCES trucks(id),
                FOREIGN KEY (authorized_by) REFERENCES users(id)
            );

            INSERT INTO deliveries_migrated (
                id, delivery_code, order_id, driver_id, truck_id, delivery_window, delivery_status,
                current_lat, current_lng, last_gps_update, recipient_received_by, recipient_role,
                delivery_notes, quantity_received, completion_time, recipient_acknowledged, proof_file, delivered_at,
                authorized_by, authorized_at
            )
            SELECT
                id, delivery_code, order_id, driver_id, truck_id, delivery_window, delivery_status,
                current_lat, current_lng, last_gps_update, recipient_received_by, recipient_role,
                delivery_notes, quantity_received, completion_time, recipient_acknowledged, proof_file, delivered_at,
                authorized_by, authorized_at
            FROM deliveries;

            DROP TABLE deliveries;
            ALTER TABLE deliveries_migrated RENAME TO deliveries;
            PRAGMA foreign_keys = ON;
            """
        )

    user_count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        users_seed = [
            ("RML-ADM-001", "RML Admin", "admin@rml.com", "09175550100", "Purok 6, Brgy. Antipolo del Sur, Lipa City, Batangas", generate_password_hash("admin123"), "admin"),
            ("RML-DRV-014", "Juan Dela Cruz", "driver@rml.com", "09175550140", "Brgy. Marawoy, Lipa City, Batangas", generate_password_hash("driver123"), "driver"),
            ("RML-he DRV-015", "Ricardo Santos", "ricardo@rml.com", "09175551234", "Brgy. Tambo, Lipa City, Batangas", generate_password_hash("driver123"), "driver"),
            (None, "John Doe", "customer@rml.com", "09123456789", "123 Construction Ave, Lipa City, Batangas", generate_password_hash("customer123"), "customer"),
            (None, "Santos Residence", "santos@example.com", "09175550128", "Lot 12, Purok 3, Brgy. Tambo, Lipa City, Batangas", generate_password_hash("customer123"), "customer"),
            (None, "Mendoza Builders", "mendoza@example.com", "09185550199", "Brgy. Marawoy, Lipa City, Batangas", generate_password_hash("customer123"), "customer"),
        ]
        cur.executemany(
            "INSERT INTO users (staff_id, name, email, phone, address, password_hash, role) VALUES (?, ?, ?, ?, ?, ?, ?)",
            users_seed,
        )

        categories_seed = [
            ("Cement & Aggregates", "Cement, sand, gravel, and concrete mixes"),
            ("Masonry", "Hollow blocks, culverts, and bricks"),
            ("Steel & Rebar", "Deformed steel bars and roofing sheets"),
            ("Boards & Lumber", "Plywood, gypsum boards, and framing"),
            ("Pipes & Electrical", "PVC pipes, fittings, and electrical supplies"),
        ]
        cur.executemany("INSERT INTO categories (name, description) VALUES (?, ?)", categories_seed)

        products_seed = [
            (1, "Portland Cement (40kg)", "Structural Grade Type 1P", "bag", 285.00, 320, 50, "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=500&auto=format&fit=crop"),
            (1, "Washed River Sand", "Fine grade per cubic yard", "cu.yd", 1240.00, 45, 10, "https://images.unsplash.com/photo-1508873535684-277a3cbcc4e8?w=500&auto=format&fit=crop"),
            (1, "Crushed Gravel (3/4\")", "Concrete aggregate per ton", "ton", 980.00, 60, 15, "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=500&auto=format&fit=crop"),
            (2, "Hollow Blocks (4\")", "Load-bearing unit price", "pc", 18.50, 2400, 300, "https://images.unsplash.com/photo-1590069261209-f8e9b8642343?w=500&auto=format&fit=crop"),
            (3, "Steel Rebar (12mm)", "Deformed bar per 6m length", "pc", 312.00, 18, 25, "https://images.unsplash.com/photo-1535813547-99c456a41d4a?w=500&auto=format&fit=crop"),
            (4, "Gypsum Board (12mm)", "Standard 4'x8' sheet", "sheet", 580.00, 85, 20, "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=500&auto=format&fit=crop"),
            (5, "PVC Pipe 4\" (Orange)", "Sanitary pipe 3m length", "pc", 420.00, 110, 20, "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500&auto=format&fit=crop"),
            (3, "Corrugated Roof Sheet", "Pre-painted GI sheet 8ft", "sheet", 640.00, 14, 20, "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=500&auto=format&fit=crop"),
        ]
        cur.executemany(
            "INSERT INTO products (category_id, name, description, unit, price, stock_quantity, low_stock_threshold, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            products_seed,
        )

        trucks_seed = [
            ("RML-07", "NCB 4821", "6-Wheeler Dump Truck (10 tons)", "in_transit"),
            ("RML-03", "RML-778", "Flatbed Cargo Truck (8 tons)", "available"),
            ("RML-05", "NAA 3019", "Mini Elf Delivery Truck (4 tons)", "available"),
        ]
        cur.executemany(
            "INSERT INTO trucks (truck_code, plate_number, capacity, status) VALUES (?, ?, ?, ?)",
            trucks_seed,
        )

        cur.executemany(
            "INSERT INTO inventory_logs (product_id, movement_type, quantity, remarks, created_by) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "stock_in", 400, "Weekly cement supplier restock", 1),
                (1, "stock_out", 80, "Order #RML-1051 dispatch", 1),
                (5, "stock_out", 30, "Order #RML-1052 allocation", 1),
            ],
        )

        cur.execute(
            """
            INSERT INTO orders (order_code, customer_id, recipient_name, phone, delivery_address, preferred_date, delivery_slot, subtotal, delivery_fee, vat_amount, total_amount, order_status)
            VALUES ('#RML-9042', 4, 'John Doe', '09123456789', '123 Construction Ave, Lipa City, Batangas', '2026-11-14', 'Morning (08:00 - 12:00)', 16210.00, 1500.00, 1945.20, 19655.20, 'in_transit')
            """
        )
        o1 = cur.lastrowid
        cur.executemany(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)",
            [(o1, 1, 50, 285.00, 14250.00), (o1, 3, 2, 980.00, 1960.00)],
        )
        cur.execute(
            "INSERT INTO payments (order_id, method, reference_number, amount, payment_status) VALUES (?, 'cash', 'COD-9042', 19655.20, 'pending')",
            (o1,),
        )
        cur.execute(
            """
            INSERT INTO deliveries (delivery_code, order_id, driver_id, truck_id, delivery_window, delivery_status, current_lat, current_lng)
            VALUES ('DLV-1109-02', ?, 2, 1, '09:00 - 10:00', 'en_route', 13.9455, 121.1610)
            """,
            (o1,),
        )

        cur.execute(
            """
            INSERT INTO orders (order_code, customer_id, recipient_name, phone, delivery_address, preferred_date, delivery_slot, subtotal, delivery_fee, vat_amount, total_amount, order_status)
            VALUES ('#1051', 5, 'Engr. Paolo Santos', '09175550128', 'Lot 12, Purok 3, Brgy. Tambo, Lipa City, Batangas', '2026-11-15', 'Morning (08:00 - 12:00)', 22800.00, 1500.00, 2736.00, 27036.00, 'approved')
            """
        )
        o2 = cur.lastrowid
        cur.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, 1, 80, 285.00, 22800.00)",
            (o2,),
        )
        cur.execute(
            "INSERT INTO payments (order_id, method, reference_number, amount, payment_status) VALUES (?, 'qr', 'GCASH-88342190', 27036.00, 'pending')",
            (o2,),
        )

        cur.execute(
            """
            INSERT INTO orders (order_code, customer_id, recipient_name, phone, delivery_address, preferred_date, delivery_slot, subtotal, delivery_fee, vat_amount, total_amount, order_status)
            VALUES ('#1052', 6, 'Mendoza Builders', '09185550199', 'Brgy. Marawoy, Lipa City, Batangas', '2026-11-14', 'Afternoon (13:00 - 17:00)', 9360.00, 1500.00, 1123.20, 11983.20, 'approved')
            """
        )
        o3 = cur.lastrowid
        cur.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, 5, 30, 312.00, 9360.00)",
            (o3,),
        )
        cur.execute(
            "INSERT INTO payments (order_id, method, reference_number, amount, payment_status) VALUES (?, 'qr', 'MAYA-901234', 11983.20, 'verified')",
            (o3,),
        )
        cur.execute(
            """
            INSERT INTO deliveries (delivery_code, order_id, driver_id, truck_id, delivery_window, delivery_status, current_lat, current_lng)
            VALUES ('DLV-1109-03', ?, 2, 1, '13:00 - 14:00', 'loading', 13.9411, 121.1631)
            """,
            (o3,),
        )

    # Seed or expand full hardware catalog
    seed_catalog(cur)

    conn.commit()
    conn.close()


def create_notification(conn, user_id, title, message, notification_type="general", order_id=None):
    """Insert a notification for a user."""
    if not user_id:
        return
    try:
        conn.execute(
            """
            INSERT INTO notifications (user_id, order_id, title, message, notification_type, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, 0, datetime('now', 'localtime'))
            """,
            (user_id, order_id, title, message, notification_type),
        )
    except Exception as e:
        print(f"Error creating notification: {e}")


def sync_customer_notifications(conn, user_id):
    """Ensure customer has initial realistic notifications based on their existing orders."""
    if not user_id:
        return
    try:
        count = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ?", (user_id,)).fetchone()[0]
        if count > 0:
            return
        orders = conn.execute(
            """
            SELECT o.id, o.order_code, o.order_status, o.total_amount, o.assigned_date, o.assigned_time_slot,
                   o.created_at, d.delivery_status, d.delivery_code, p.payment_status
            FROM orders o
            LEFT JOIN deliveries d ON d.order_id = o.id
            LEFT JOIN payments p ON p.order_id = o.id
            WHERE o.customer_id = ?
            ORDER BY o.created_at ASC
            """,
            (user_id,),
        ).fetchall()

        for o in orders:
            # Order submitted notification
            conn.execute(
                """
                INSERT INTO notifications (user_id, order_id, title, message, notification_type, is_read, created_at)
                VALUES (?, ?, ?, ?, 'order', 1, ?)
                """,
                (user_id, o["id"], "Order Submitted Successfully", f"Order {o['order_code']} was placed and received by our depot.", o["created_at"]),
            )
            # Schedule proposed or confirmed
            if o["assigned_date"]:
                conn.execute(
                    """
                    INSERT INTO notifications (user_id, order_id, title, message, notification_type, is_read, created_at)
                    VALUES (?, ?, ?, ?, 'schedule', 1, ?)
                    """,
                    (user_id, o["id"], "Delivery Schedule Assigned", f"Delivery scheduled for {o['assigned_date']} ({o['assigned_time_slot']}).", o["created_at"]),
                )
            # Payment status
            if o["payment_status"] == "verified":
                conn.execute(
                    """
                    INSERT INTO notifications (user_id, order_id, title, message, notification_type, is_read, created_at)
                    VALUES (?, ?, ?, ?, 'payment', 1, ?)
                    """,
                    (user_id, o["id"], "Payment Verified", f"Payment for order {o['order_code']} has been verified and confirmed.", o["created_at"]),
                )
            # Delivery status
            if o["delivery_status"] == "delivered" or o["order_status"] == "delivered":
                conn.execute(
                    """
                    INSERT INTO notifications (user_id, order_id, title, message, notification_type, is_read, created_at)
                    VALUES (?, ?, ?, ?, 'delivery', 1, ?)
                    """,
                    (user_id, o["id"], "Order Delivered", f"Order {o['order_code']} has been successfully delivered and acknowledged at your site.", o["created_at"]),
                )
            elif o["order_status"] == "cancelled":
                conn.execute(
                    """
                    INSERT INTO notifications (user_id, order_id, title, message, notification_type, is_read, created_at)
                    VALUES (?, ?, ?, ?, 'order', 1, ?)
                    """,
                    (user_id, o["id"], "Order Cancelled", f"Order {o['order_code']} has been cancelled.", o["created_at"]),
                )
        conn.commit()
    except Exception as e:
        print(f"Error syncing notifications: {e}")


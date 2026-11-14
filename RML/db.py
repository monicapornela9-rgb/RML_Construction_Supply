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


def init_db():
    """Create tables if they do not exist and seed initial sample data."""
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
            role TEXT NOT NULL CHECK(role IN ('admin', 'customer', 'driver')),
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
            order_status TEXT NOT NULL DEFAULT 'pending'
                CHECK(order_status IN ('pending', 'approved', 'rejected', 'preparing', 'in_transit', 'delivered')),
            rejection_reason TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (customer_id) REFERENCES users(id)
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
            amount REAL NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'pending'
                CHECK(payment_status IN ('pending', 'verified', 'rejected')),
            paid_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_code TEXT NOT NULL UNIQUE,
            order_id INTEGER NOT NULL UNIQUE,
            driver_id INTEGER,
            truck_id INTEGER,
            delivery_window TEXT,
            delivery_status TEXT NOT NULL DEFAULT 'queued'
                CHECK(delivery_status IN ('queued', 'assigned', 'loading', 'en_route', 'delivered')),
            current_lat REAL DEFAULT 13.9411,
            current_lng REAL DEFAULT 121.1631,
            last_gps_update TEXT,
            recipient_received_by TEXT,
            recipient_role TEXT,
            delivery_notes TEXT,
            delivered_at TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (driver_id) REFERENCES users(id),
            FOREIGN KEY (truck_id) REFERENCES trucks(id)
        );
        """
    )

    user_count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        users_seed = [
            ("RML-ADM-001", "RML Admin", "admin@rml.com", "09175550100", "Purok 6, Brgy. Antipolo del Sur, Lipa City, Batangas", generate_password_hash("admin123"), "admin"),
            ("RML-DRV-014", "Juan Dela Cruz", "driver@rml.com", "09175550140", "Brgy. Marawoy, Lipa City, Batangas", generate_password_hash("driver123"), "driver"),
            ("RML-DRV-015", "Ricardo Santos", "ricardo@rml.com", "09175551234", "Brgy. Tambo, Lipa City, Batangas", generate_password_hash("driver123"), "driver"),
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
            VALUES ('#1051', 5, 'Engr. Paolo Santos', '09175550128', 'Lot 12, Purok 3, Brgy. Tambo, Lipa City, Batangas', '2026-11-15', 'Morning (08:00 - 12:00)', 22800.00, 1500.00, 2736.00, 27036.00, 'pending')
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

    conn.commit()
    conn.close()

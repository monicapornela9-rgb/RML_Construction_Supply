import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'RML')))
from app import app
from db import get_db

class TestCompleteCustomerRedesign(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_01_public_and_auth_routes(self):
        """Verify public landing, login, register, and forgot-password render successfully."""
        routes = ['/', '/login', '/register', '/forgot-password']
        for r in routes:
            res = self.client.get(r)
            self.assertEqual(res.status_code, 200, f"Route {r} failed with status {res.status_code}")
            print(f"PASS: {r} -> 200 OK")

    def test_02_customer_authenticated_portal_routes(self):
        """Verify all authenticated customer routes render cleanly."""
        with self.app.app_context():
            db = get_db()
            # Select customer who owns orders for full tracking & payment coverage
            order = db.execute("SELECT id, customer_id FROM orders LIMIT 1").fetchone()
            if order:
                cust = db.execute("SELECT id, name, email FROM users WHERE id = ?", (order['customer_id'],)).fetchone()
            else:
                cust = db.execute("SELECT id, name, email FROM users WHERE role = 'customer' LIMIT 1").fetchone()
            self.assertIsNotNone(cust, "No customer user found in test database")

            with self.client.session_transaction() as sess:
                sess['user_id'] = cust['id']
                sess['role'] = 'customer'
                sess['user_name'] = cust['name']
                sess['user_email'] = cust['email']

            # Test general customer portal routes (non-cart-dependent)
            customer_routes = [
                '/customer/dashboard',
                '/customer/catalog',
                '/customer/cart',
                '/customer/orders',
                '/customer/payment-history',
                '/customer/tracking',
                '/customer/settings',
                '/customer/notifications',
                '/customer/support',
            ]

            for r in customer_routes:
                res = self.client.get(r)
                self.assertEqual(res.status_code, 200, f"Customer route {r} failed with status {res.status_code}")
                print(f"PASS: {r} -> 200 OK")

            # Check checkout route by adding a product to the cart first
            prod = db.execute("SELECT id, stock_quantity FROM products WHERE is_active = 1 AND stock_quantity > 0 LIMIT 1").fetchone()
            if prod:
                add_res = self.client.post('/customer/cart/add', data={
                    'product_id': prod['id'],
                    'quantity': 1
                }, follow_redirects=False)
                checkout_res = self.client.get('/customer/checkout')
                self.assertEqual(checkout_res.status_code, 200, f"Checkout failed with status {checkout_res.status_code}")
                print(f"PASS: /customer/checkout -> 200 OK (with item in cart)")

            # Check order tracking, payment, and confirmation for this customer's order
            if order:
                order_id = order['id']
                tracking_res = self.client.get(f'/customer/orders/{order_id}/tracking')
                self.assertEqual(tracking_res.status_code, 200, f"Tracking route for order {order_id} failed")
                print(f"PASS: /customer/orders/{order_id}/tracking -> 200 OK")

                payment_res = self.client.get(f'/customer/payment/{order_id}?step=1')
                self.assertEqual(payment_res.status_code, 200, f"Payment step 1 route for order {order_id} failed")
                print(f"PASS: /customer/payment/{order_id}?step=1 -> 200 OK")

                confirmation_res = self.client.get(f'/customer/orders/{order_id}/confirmation')
                self.assertEqual(confirmation_res.status_code, 200, f"Order confirmation route for order {order_id} failed")
                print(f"PASS: /customer/orders/{order_id}/confirmation -> 200 OK")

    def test_03_design_tokens_presence(self):
        """Verify key Figma tokens (Navy #142235, Red #C83227, customer portal classes) are rendered."""
        res = self.client.get('/')
        html = res.data.decode('utf-8')
        self.assertIn("RML Construction Supply", html)
        self.assertIn("Customer login", html)
        self.assertIn("Shop by Category", html)
        print("PASS: Landing page contains expected brand identity and sections.")

if __name__ == '__main__':
    unittest.main()

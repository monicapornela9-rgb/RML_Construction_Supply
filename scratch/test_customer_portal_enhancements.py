import sys
import os
import unittest
import sqlite3
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'RML')))
from app import app
from db import get_db, DB_PATH
from werkzeug.security import generate_password_hash, check_password_hash


class CustomerPortalComprehensiveTest(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def login_as(self, identifier, password):
        return self.client.post("/login", data={"identifier": identifier, "password": password}, follow_redirects=True)

    def set_session(self, user_id=7, role="customer", user_name="Monica", user_email="kirvee518@gmail.com"):
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["role"] = role
            sess["user_name"] = user_name
            sess["user_email"] = user_email

    def test_01_customer_login_and_logout(self):
        """1. Customer login and logout with proper session handling."""
        # Valid login with registered customer (Santos Residence)
        resp = self.login_as("santos@example.com", "customer123")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        self.assertIn("Customer Portal", html)
        self.assertIn("Welcome back, Santos Residence", html)

        # Session verification
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("role"), "customer")
            self.assertEqual(sess.get("user_id"), 5)

        # Logout
        resp_logout = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(resp_logout.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)

    def test_02_dashboard_overview_and_statistics(self):
        """2. Dashboard overview and statistics (NO profile edit forms on dashboard)."""
        self.set_session(user_id=7, role="customer", user_name="Monica", user_email="kirvee518@gmail.com")
        resp = self.client.get("/customer/dashboard")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")

        # Must display customer name and metrics
        self.assertIn("Welcome back, Monica", html)
        self.assertIn("Total Orders", html)
        self.assertIn("Pending Orders", html)
        self.assertIn("In Processing", html)
        self.assertIn("Active Deliveries", html)

        # CRITICAL: Must NOT contain editable profile fields or profile update forms on the dashboard
        self.assertNotIn('action="update_profile"', html)
        self.assertNotIn('action="update_settings"', html)
        self.assertNotIn('name="current_password"', html)
        self.assertNotIn('name="new_password"', html)
        self.assertNotIn('Save Profile Details', html)
        self.assertNotIn('Update Password', html)

        # Recent orders must be visible on the clean full-width dashboard
        self.assertIn("Recently Placed Orders", html)
        self.assertIn("#RML-6320", html)

        # Removed right-column sections must NOT appear on dashboard
        self.assertNotIn("Quick Action Hub", html)
        self.assertNotIn("Recent Order &amp; Delivery Updates", html)
        self.assertNotIn("Recent Order & Delivery Updates", html)
        self.assertNotIn("Lipa City Central Depot", html)

    def test_03_product_browsing_and_searching(self):
        """3. Product browsing and searching."""
        self.set_session(user_id=7, role="customer", user_name="Monica")
        resp = self.client.get("/customer/catalog")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        self.assertIn("Construction Materials", html)

        # Search for thinner
        resp_search = self.client.get("/customer/catalog?q=Thinner")
        self.assertEqual(resp_search.status_code, 200)
        self.assertIn(b"Thinner", resp_search.data)

    def test_04_cart_management(self):
        """4. Adding, changing quantities, and removing cart items with database-backed isolation."""
        self.set_session(user_id=7, role="customer", user_name="Monica")
        
        # Ensure user 7 cart starts clean
        conn = get_db()
        conn.execute("DELETE FROM cart_items WHERE user_id = 7")
        conn.commit()
        conn.close()

        # Step 1: Empty cart view verification
        resp_empty = self.client.get("/customer/cart")
        self.assertEqual(resp_empty.status_code, 200)
        html_empty = resp_empty.data.decode("utf-8")
        self.assertIn("Your shopping cart is empty.", html_empty)
        self.assertIn("Browse our catalog and add construction materials to get started.", html_empty)
        self.assertIn("Browse Materials Catalog", html_empty)

        # Step 2: Add item 11 (KB Denatured Alcohol, active stock)
        resp_add = self.client.post("/customer/cart/add", data={"product_id": 11, "quantity": 2}, follow_redirects=True)
        self.assertEqual(resp_add.status_code, 200)

        # Verify database record in cart_items for user 7
        conn = get_db()
        db_items = conn.execute("SELECT * FROM cart_items WHERE user_id = 7").fetchall()
        self.assertEqual(len(db_items), 1)
        self.assertEqual(db_items[0]["product_id"], 11)
        self.assertEqual(db_items[0]["quantity"], 2)
        cart_item_id = db_items[0]["id"]
        conn.close()

        # Step 3: Add the same item again (quantity +3) -> Should update existing row without duplicates
        resp_add_again = self.client.post("/customer/cart/add", data={"product_id": 11, "quantity": 3}, follow_redirects=True)
        self.assertEqual(resp_add_again.status_code, 200)

        conn = get_db()
        db_items = conn.execute("SELECT * FROM cart_items WHERE user_id = 7").fetchall()
        self.assertEqual(len(db_items), 1, "Duplicate row created instead of updating quantity")
        self.assertEqual(db_items[0]["quantity"], 5)
        conn.close()

        # Step 4: Verify Cart page displays the item, price, subtotals, and delivery fee
        resp_cart = self.client.get("/customer/cart")
        self.assertEqual(resp_cart.status_code, 200)
        html_cart = resp_cart.data.decode("utf-8")
        self.assertIn("KB Denatured Alcohol", html_cart)
        self.assertIn("Selected Materials", html_cart)
        self.assertIn("Standard Delivery Fee", html_cart)
        self.assertIn("Proceed to Checkout", html_cart)

        # Step 5: Update quantity via cart_update
        resp_update = self.client.post("/customer/cart/update", data={"cart_item_id": cart_item_id, "quantity": 3}, follow_redirects=True)
        self.assertEqual(resp_update.status_code, 200)
        conn = get_db()
        db_item = conn.execute("SELECT quantity FROM cart_items WHERE id = ?", (cart_item_id,)).fetchone()
        self.assertEqual(db_item["quantity"], 3)
        conn.close()

        # Step 6: Customer Isolation check
        # Switch session to user 5 (Santos Residence) - Cart must be empty and unable to see or modify user 7's cart
        self.set_session(user_id=5, role="customer", user_name="Santos Residence", user_email="santos@example.com")
        resp_user5_cart = self.client.get("/customer/cart")
        self.assertEqual(resp_user5_cart.status_code, 200)
        self.assertIn("Your shopping cart is empty.", resp_user5_cart.data.decode("utf-8"))

        # User 5 cannot update or delete User 7's cart item
        self.client.post("/customer/cart/update", data={"cart_item_id": cart_item_id, "quantity": 99}, follow_redirects=True)
        self.client.post(f"/customer/cart/remove/{cart_item_id}", follow_redirects=True)
        conn = get_db()
        user7_item = conn.execute("SELECT quantity FROM cart_items WHERE id = ?", (cart_item_id,)).fetchone()
        self.assertIsNotNone(user7_item, "Cross-customer deletion occurred!")
        self.assertEqual(user7_item["quantity"], 3, "Cross-customer modification occurred!")
        conn.close()

        # Switch back to user 7
        self.set_session(user_id=7, role="customer", user_name="Monica")

        # Step 7: Remove item via /customer/cart/remove/<id>
        resp_remove = self.client.post(f"/customer/cart/remove/{cart_item_id}", follow_redirects=True)
        self.assertEqual(resp_remove.status_code, 200)
        conn = get_db()
        remaining = conn.execute("SELECT COUNT(*) FROM cart_items WHERE user_id = 7").fetchone()[0]
        self.assertEqual(remaining, 0)
        conn.close()

        # Step 8: Clear Cart test
        # Add two items
        self.client.post("/customer/cart/add", data={"product_id": 11, "quantity": 1}, follow_redirects=True)
        self.client.post("/customer/cart/add", data={"product_id": 12, "quantity": 2}, follow_redirects=True)
        conn = get_db()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cart_items WHERE user_id = 7").fetchone()[0], 2)
        conn.close()

        # Post to clear cart
        resp_clear = self.client.post("/customer/cart/clear", follow_redirects=True)
        self.assertEqual(resp_clear.status_code, 200)
        conn = get_db()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cart_items WHERE user_id = 7").fetchone()[0], 0)
        conn.close()

    def test_05_checkout_and_order_submission(self):
        """5. Checkout and order submission with empty cart guard and post-submission cart clearing."""
        self.set_session(user_id=7, role="customer", user_name="Monica")

        # Ensure user 7 cart is clean first
        conn = get_db()
        conn.execute("DELETE FROM cart_items WHERE user_id = 7")
        conn.commit()
        conn.close()

        # Step 1: Empty cart access to checkout should redirect to cart
        resp_empty_checkout = self.client.get("/customer/checkout", follow_redirects=True)
        self.assertEqual(resp_empty_checkout.status_code, 200)
        self.assertIn("Your shopping cart is empty", resp_empty_checkout.data.decode("utf-8"))

        # Step 2: Add 1 item 11 (KB Denatured Alcohol) to cart
        self.client.post("/customer/cart/add", data={"product_id": 11, "quantity": 1}, follow_redirects=True)

        # Step 3: Checkout page should now render properly with order review
        resp_checkout_get = self.client.get("/customer/checkout")
        self.assertEqual(resp_checkout_get.status_code, 200)
        html_checkout = resp_checkout_get.data.decode("utf-8")
        self.assertIn("Delivery &amp; Site Details", html_checkout)
        self.assertIn("Order Review", html_checkout)
        self.assertIn("KB Denatured Alcohol", html_checkout)
        self.assertIn("Submit Order for Scheduling", html_checkout)

        test_order_id = None
        try:
            # Step 4: Submit checkout
            resp = self.client.post("/customer/checkout", data={
                "recipient_name": "Test Suite Recipient",
                "phone": "09171234567",
                "delivery_address": "Brgy. Marawoy, Lipa City, Batangas",
                "special_instructions": "Gate 2 test delivery"
            }, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            # Step 5: Verify cart in DB was emptied after order placement
            conn = get_db()
            cart_after = conn.execute("SELECT COUNT(*) FROM cart_items WHERE user_id = 7").fetchone()[0]
            self.assertEqual(cart_after, 0, "Cart was not cleared after successful checkout!")

            # Find created test order
            row = conn.execute("SELECT id, order_code, customer_id FROM orders WHERE recipient_name = 'Test Suite Recipient' ORDER BY id DESC LIMIT 1").fetchone()
            self.assertIsNotNone(row)
            test_order_id = row["id"]
            self.assertEqual(row["customer_id"], 7)

            # Check that an order notification was generated
            notif = conn.execute("SELECT * FROM notifications WHERE order_id = ?", (test_order_id,)).fetchone()
            self.assertIsNotNone(notif)
            self.assertEqual(notif["user_id"], 7)
            conn.close()

        finally:
            # Clean up test order to keep database pristine
            if test_order_id:
                conn = get_db()
                conn.execute("DELETE FROM order_items WHERE order_id = ?", (test_order_id,))
                conn.execute("DELETE FROM deliveries WHERE order_id = ?", (test_order_id,))
                conn.execute("DELETE FROM payments WHERE order_id = ?", (test_order_id,))
                conn.execute("DELETE FROM notifications WHERE order_id = ?", (test_order_id,))
                conn.execute("DELETE FROM orders WHERE id = ?", (test_order_id,))
                conn.commit()
                conn.close()

    def test_06_and_07_viewing_order_history_and_details(self):
        """6 & 7. Viewing personal order history, details, and statuses."""
        self.set_session(user_id=7, role="customer", user_name="Monica")
        # My Orders page
        resp = self.client.get("/customer/orders")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        self.assertIn("My Orders", html)
        self.assertIn("#RML-6320", html)

        # Order tracking / details view for own order #4
        resp_details = self.client.get("/customer/orders/4/tracking")
        self.assertEqual(resp_details.status_code, 200)
        self.assertIn(b"RML-6320", resp_details.data)

    def test_08_delivery_tracking_overview(self):
        """8. Viewing delivery updates & schedules on /customer/tracking."""
        self.set_session(user_id=7, role="customer", user_name="Monica")
        resp = self.client.get("/customer/tracking")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        self.assertIn("Delivery Tracking", html)
        self.assertIn("Total Dispatches", html)
        self.assertIn("Active Dispatches", html)
        self.assertIn("Completed Deliveries", html)
        self.assertIn("#RML-6320", html)

    def test_09_notifications_and_mark_as_read(self):
        """9. Receiving notifications and marking as read."""
        self.set_session(user_id=7, role="customer", user_name="Monica")
        # Notifications page loads
        resp = self.client.get("/customer/notifications")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        self.assertIn("Notifications &amp; Activity", html)

        conn = get_db()
        notifs = conn.execute("SELECT id, is_read FROM notifications WHERE user_id = 7").fetchall()
        self.assertTrue(len(notifs) > 0)
        target_notif = notifs[0]

        # Mark single notification as read
        resp_read = self.client.post(f"/customer/notifications/{target_notif['id']}/read", follow_redirects=True)
        self.assertEqual(resp_read.status_code, 200)

        # Mark all as read
        resp_all = self.client.post("/customer/notifications/mark-all-read", follow_redirects=True)
        self.assertEqual(resp_all.status_code, 200)
        unread = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id = 7 AND is_read = 0").fetchone()[0]
        self.assertEqual(unread, 0)
        conn.close()

    def test_10_settings_profile_update(self):
        """10. Editing profile information through Settings only."""
        # Test on Santos Residence (user_id=5)
        self.set_session(user_id=5, role="customer", user_name="Santos Residence", user_email="santos@example.com")

        # Access Settings page
        resp = self.client.get("/customer/settings")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Account Settings &amp; Security", resp.data)

        # Also verify /customer/profile works as an alias
        resp_profile = self.client.get("/customer/profile")
        self.assertEqual(resp_profile.status_code, 200)
        self.assertIn(b"Account Settings &amp; Security", resp_profile.data)

        # Update profile with valid data
        resp_update = self.client.post("/customer/settings", data={
            "action": "update_settings",
            "name": "Santos Residence Updated",
            "email": "santos@example.com",
            "phone": "09175550128",
            "address": "Lot 12, Purok 3, Brgy. Tambo, Lipa City, Batangas"
        }, follow_redirects=True)
        self.assertEqual(resp_update.status_code, 200)
        self.assertIn(b"updated successfully", resp_update.data)

        conn = get_db()
        user = conn.execute("SELECT name FROM users WHERE id = 5").fetchone()
        self.assertEqual(user["name"], "Santos Residence Updated")

        # Restore original name
        conn.execute("UPDATE users SET name = 'Santos Residence' WHERE id = 5")
        conn.commit()
        conn.close()

    def test_11_settings_password_change(self):
        """11. Changing passwords through Settings with strict validation."""
        # Test password changes on Santos Residence (user_id=5) whose initial password is customer123
        self.set_session(user_id=5, role="customer", user_name="Santos Residence", user_email="santos@example.com")

        # Wrong current password
        resp_wrong = self.client.post("/customer/settings", data={
            "action": "change_password",
            "current_password": "WrongPassword123!",
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!"
        }, follow_redirects=True)
        self.assertIn(b"Current password is incorrect", resp_wrong.data)

        # Short password (< 8 chars)
        resp_short = self.client.post("/customer/settings", data={
            "action": "change_password",
            "current_password": "customer123",
            "new_password": "Short!",
            "confirm_password": "Short!"
        }, follow_redirects=True)
        self.assertIn(b"Password must be at least 8 characters", resp_short.data)

        # Successful password update
        resp_ok = self.client.post("/customer/settings", data={
            "action": "change_password",
            "current_password": "customer123",
            "new_password": "RmlCustomer2026!",
            "confirm_password": "RmlCustomer2026!"
        }, follow_redirects=True)
        self.assertIn(b"Password updated successfully", resp_ok.data)

        # Verify new password is valid in DB
        conn = get_db()
        user = conn.execute("SELECT password_hash FROM users WHERE id = 5").fetchone()
        self.assertTrue(check_password_hash(user["password_hash"], "RmlCustomer2026!"))

        # Restore password back to customer123
        conn.execute("UPDATE users SET password_hash = ? WHERE id = 5", (generate_password_hash("customer123"),))
        conn.commit()
        conn.close()

    def test_12_prevent_cross_customer_access(self):
        """12. Preventing customers from accessing other customers' information."""
        # Customer 7 (Monica) tries to access Customer 10's order (order #22)
        self.set_session(user_id=7, role="customer", user_name="Monica", user_email="kirvee518@gmail.com")

        # Attempt to access Customer 10's order tracking
        resp = self.client.get("/customer/orders/22/tracking", follow_redirects=True)
        html = resp.data.decode("utf-8")
        self.assertTrue("Unauthorized access" in html or "My Orders" in html)

        # Attempt to access Customer 10's payment
        resp_pay = self.client.get("/customer/payment/22", follow_redirects=True)
        html_pay = resp_pay.data.decode("utf-8")
        self.assertTrue("Unauthorized access" in html_pay or "My Orders" in html_pay)

    def test_13_prevent_customer_access_to_admin_and_driver(self):
        """13. Preventing customers from accessing Admin and Driver pages."""
        self.set_session(user_id=7, role="customer", user_name="Monica", user_email="kirvee518@gmail.com")

        # Attempt Admin Dashboard
        resp_admin = self.client.get("/admin/dashboard", follow_redirects=True)
        html_admin = resp_admin.data.decode("utf-8")
        self.assertIn("Access denied", html_admin)
        self.assertIn("Customer Portal", html_admin)

        # Attempt Driver Dashboard
        resp_driver = self.client.get("/driver/dashboard", follow_redirects=True)
        html_driver = resp_driver.data.decode("utf-8")
        self.assertIn("Access denied", html_driver)


if __name__ == "__main__":
    unittest.main()

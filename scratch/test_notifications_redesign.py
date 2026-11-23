import unittest
import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "RML")))
from app import app
from db import get_db

class TestCustomerNotificationsAndDashboard(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

    def set_session(self, user_id=7, role="customer", user_name="Monica", user_email="kirvee518@gmail.com"):
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["role"] = role
            sess["user_name"] = user_name
            sess["user_email"] = user_email
            sess["_fresh"] = True

    def test_dashboard_clean_layout_and_navigation(self):
        """Verify Customer Dashboard has removed Quick Action Hub, Updates, and Depot sections while keeping table full-width."""
        self.set_session(user_id=7, role="customer", user_name="Monica")
        resp = self.client.get("/customer/dashboard")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")

        # 1. Removed sections must NOT be present on the dashboard
        self.assertNotIn("Quick Action Hub", html)
        self.assertNotIn("Recent Order &amp; Delivery Updates", html)
        self.assertNotIn("Recent Order & Delivery Updates", html)
        self.assertNotIn("Lipa City Central Depot", html)

        # 2. Recently placed orders table is intact and prominent
        self.assertIn("Recently Placed Orders", html)
        self.assertIn("#RML-6320", html)

        # 3. Key functionalities remain accessible via navbar/banner links
        self.assertIn("/customer/catalog", html)
        self.assertIn("/customer/orders", html)
        self.assertIn("/customer/tracking", html)

    def test_notifications_page_renders_with_required_elements(self):
        """Verify Notifications page displays real customer notifications with required elements."""
        self.set_session(user_id=7, role="customer", user_name="Monica")
        resp = self.client.get("/customer/notifications")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")

        # Header and section
        self.assertIn("Notifications &amp; Activity", html)
        self.assertIn("Recent Order &amp; Delivery Updates", html)

        # Check required notification types exist for customer 7
        self.assertIn("Order Submitted Successfully", html)
        self.assertIn("Delivery Schedule Assigned", html)
        self.assertIn("Payment Verified", html)
        self.assertIn("Order Delivered", html)

        # Each notification must have a View Order link
        self.assertIn("View Order Details", html)
        self.assertIn("/customer/orders/", html)

        # Timestamps must be present
        self.assertIn("2026-", html)

    def test_notifications_for_user_38(self):
        """Verify notifications for User 38 (which has Payment Submitted, Ready for Dispatch, Order Cancelled)."""
        self.set_session(user_id=38, role="customer", user_name="Redena")
        resp = self.client.get("/customer/notifications")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")

        self.assertIn("Order Submitted Successfully", html)
        self.assertIn("Delivery Schedule Proposed", html)
        self.assertIn("Schedule Confirmed", html)
        self.assertIn("Payment Submitted", html)
        self.assertIn("Ready for Dispatch", html)
        self.assertIn("Order Cancelled", html)

        # Check filtering
        resp_orders = self.client.get("/customer/notifications?type=order")
        self.assertEqual(resp_orders.status_code, 200)
        html_orders = resp_orders.data.decode("utf-8")
        self.assertIn("Order Submitted Successfully", html_orders)

    def test_notification_mark_read_and_mark_all_read(self):
        """Verify mark read and mark all read functionality."""
        self.set_session(user_id=38, role="customer", user_name="Redena")
        conn = get_db()
        notifs = conn.execute("SELECT id, is_read FROM notifications WHERE user_id = 38").fetchall()
        self.assertTrue(len(notifs) > 0)
        first_id = notifs[0]["id"]
        conn.close()

        # Mark single
        resp_read = self.client.post(f"/customer/notifications/{first_id}/read", follow_redirects=True)
        self.assertEqual(resp_read.status_code, 200)

        # Mark all read
        resp_all = self.client.post("/customer/notifications/mark-all-read", follow_redirects=True)
        self.assertEqual(resp_all.status_code, 200)

        conn = get_db()
        unread_count = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id = 38 AND is_read = 0").fetchone()[0]
        self.assertEqual(unread_count, 0)
        conn.close()

if __name__ == "__main__":
    unittest.main()

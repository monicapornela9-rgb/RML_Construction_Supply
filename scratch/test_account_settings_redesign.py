import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "RML")))
from app import app
from db import get_db
from werkzeug.security import check_password_hash, generate_password_hash

class TestAccountSettingsRedesign(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

    def set_session(self, user_id=5, role="customer", user_name="Santos Residence", user_email="santos@example.com"):
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["role"] = role
            sess["user_name"] = user_name
            sess["user_email"] = user_email
            sess["_fresh"] = True

    def test_settings_page_ui_and_components(self):
        """Verify redesigned Account Settings & Security page elements."""
        self.set_session(user_id=5)
        resp = self.client.get("/customer/settings")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")

        # 1. Page Header
        self.assertIn("Account Settings &amp; Security", html)
        self.assertIn("Manage your personal information, delivery site addresses, and login credentials.", html)

        # 2. Compact Modern Profile Card (No oversized dark gradient banner)
        self.assertNotIn("linear-gradient(135deg, #142235 0%, #1e3352 100%)", html)
        self.assertIn("settings-profile-card", html)
        self.assertIn("Santos Residence", html)
        self.assertIn("#CUST-0005", html)
        self.assertIn("Active Account", html)
        self.assertIn("Member Since", html)
        self.assertIn("Total Orders", html)

        # 3. Personal & Delivery Form
        self.assertIn("Personal &amp; Delivery Information", html)
        self.assertIn('name="action" value="update_settings"', html)
        self.assertIn('name="name"', html)
        self.assertIn('name="email"', html)
        self.assertIn('name="phone"', html)
        self.assertIn('name="address"', html)
        self.assertIn("Save Changes", html)

        # 4. Change Password Form
        self.assertIn("Change Account Password", html)
        self.assertIn('name="action" value="change_password"', html)
        self.assertIn('name="current_password"', html)
        self.assertIn('name="new_password"', html)
        self.assertIn('name="confirm_password"', html)
        self.assertIn("Update Password", html)
        self.assertIn("togglePasswordVisibility", html)

        # 5. Support Section
        self.assertIn("Need help updating your account details or delivery site info?", html)
        self.assertIn("Contact RML Support", html)

    def test_profile_update_and_restore(self):
        """Verify profile update saves correctly to SQLite."""
        self.set_session(user_id=5)
        resp = self.client.post("/customer/settings", data={
            "action": "update_settings",
            "name": "Santos Residence Modernized",
            "email": "santos@example.com",
            "phone": "09175550128",
            "address": "Block 5, Lot 10, Brgy. Marawoy, Lipa City, Batangas"
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"updated successfully", resp.data)

        conn = get_db()
        row = conn.execute("SELECT name, phone, address FROM users WHERE id = 5").fetchone()
        self.assertEqual(row["name"], "Santos Residence Modernized")
        self.assertEqual(row["phone"], "09175550128")
        self.assertEqual(row["address"], "Block 5, Lot 10, Brgy. Marawoy, Lipa City, Batangas")

        # Restore
        conn.execute("UPDATE users SET name = 'Santos Residence', address = 'Lipa City, Batangas' WHERE id = 5")
        conn.commit()
        conn.close()

    def test_password_change_and_validation(self):
        """Verify password update works with validation and restores properly."""
        self.set_session(user_id=5)

        # Wrong password
        resp_wrong = self.client.post("/customer/settings", data={
            "action": "change_password",
            "current_password": "IncorrectPassword123!",
            "new_password": "NewStrongPassword2026!",
            "confirm_password": "NewStrongPassword2026!"
        }, follow_redirects=True)
        self.assertIn(b"Current password is incorrect", resp_wrong.data)

        # Valid password change
        resp_valid = self.client.post("/customer/settings", data={
            "action": "change_password",
            "current_password": "customer123",
            "new_password": "RmlModernPassword2026!",
            "confirm_password": "RmlModernPassword2026!"
        }, follow_redirects=True)
        self.assertIn(b"Password updated successfully", resp_valid.data)

        # Verify DB hash
        conn = get_db()
        user = conn.execute("SELECT password_hash FROM users WHERE id = 5").fetchone()
        self.assertTrue(check_password_hash(user["password_hash"], "RmlModernPassword2026!"))

        # Restore original password
        conn.execute("UPDATE users SET password_hash = ? WHERE id = 5", (generate_password_hash("customer123"),))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    unittest.main()

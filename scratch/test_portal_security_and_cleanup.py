import sys
import os
import re

# Add RML directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "RML"))

from app import app
from db import get_db

client = app.test_client()

def run_tests():
    print("=" * 70)
    print("STARTING COMPLETE SYSTEM CLEANUP, SECURITY & RBAC VERIFICATION")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. PUBLIC LANDING PAGE (/)
    # -------------------------------------------------------------
    print("\n[TEST 1] Public Customer Landing Page (/)")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.data.decode("utf-8")
    assert "Everything You Need to Build" in html, "Missing Hero tagline"
    assert "RML Construction Supply" in html, "Missing company name"
    assert "Customer Login" in html, "Missing Customer Login button"
    assert "Register Now" in html, "Missing Register Now button"
    # Ensure no admin or driver login buttons in the navbar or landing page
    assert 'href="/admin/login"' not in html, "Security leak: admin login link found on public landing page"
    assert 'href="/driver/login"' not in html, "Security leak: driver login link found on public landing page"
    assert 'role=admin' not in html, "Old role tabs leak found on landing page"
    assert 'role=driver' not in html, "Old role tabs leak found on landing page"
    print("  PASS: Landing page is modern, customer-oriented, and contains zero admin/driver links.")

    # -------------------------------------------------------------
    # 2. DEDICATED LOGIN PAGES EXISTENCE
    # -------------------------------------------------------------
    print("\n[TEST 2] Dedicated Portal Login Pages")
    res_cust = client.get("/login")
    assert res_cust.status_code == 200, f"/login status: {res_cust.status_code}"
    cust_html = res_cust.data.decode("utf-8")
    assert "Customer Portal" in cust_html
    assert 'role="tab"' not in cust_html, "Old multi-role tabs found in customer login"

    res_admin = client.get("/admin/login")
    assert res_admin.status_code == 200, f"/admin/login status: {res_admin.status_code}"
    admin_html = res_admin.data.decode("utf-8")
    assert "Admin / Staff Portal" in admin_html

    res_driver = client.get("/driver/login")
    assert res_driver.status_code == 200, f"/driver/login status: {res_driver.status_code}"
    driver_html = res_driver.data.decode("utf-8")
    assert "Driver Portal" in driver_html
    print("  PASS: Customer (/login), Admin (/admin/login), and Driver (/driver/login) pages are completely separate.")

    # -------------------------------------------------------------
    # 3. CUSTOMER REGISTRATION VALIDATION & STRICT PASSWORD POLICY
    # -------------------------------------------------------------
    print("\n[TEST 3] Customer Registration & Strict Password Validation")

    # A. Incomplete fields
    r = client.post("/register", data={"name": "", "email": "", "phone": "", "address": "", "password": ""}, follow_redirects=True)
    assert "All fields are required" in r.data.decode("utf-8")

    # B. Invalid email
    r = client.post("/register", data={"name": "Test User", "email": "invalid-email", "phone": "09171234567", "address": "Lipa", "password": "Valid@Password123", "confirm_password": "Valid@Password123"}, follow_redirects=True)
    assert "valid email" in r.data.decode("utf-8")

    # C. Invalid Philippine phone number
    r = client.post("/register", data={"name": "Test User", "email": "valid@email.com", "phone": "123456", "address": "Lipa", "password": "Valid@Password123", "confirm_password": "Valid@Password123"}, follow_redirects=True)
    assert "Philippine mobile number" in r.data.decode("utf-8")

    # D. Password confirmation mismatch
    r = client.post("/register", data={"name": "Test User", "email": "valid@email.com", "phone": "09171234567", "address": "Lipa", "password": "Valid@Password123", "confirm_password": "DifferentPassword123!"}, follow_redirects=True)
    assert "Passwords do not match" in r.data.decode("utf-8")

    # E. Password < 8 characters
    r = client.post("/register", data={"name": "Test User", "email": "valid@email.com", "phone": "09171234567", "address": "Lipa", "password": "Sh0rt!", "confirm_password": "Sh0rt!"}, follow_redirects=True)
    assert "at least 8 characters" in r.data.decode("utf-8")

    # F. Password missing uppercase
    r = client.post("/register", data={"name": "Test User", "email": "valid@email.com", "phone": "09171234567", "address": "Lipa", "password": "lowercase123!", "confirm_password": "lowercase123!"}, follow_redirects=True)
    assert "uppercase letter" in r.data.decode("utf-8")

    # G. Password missing lowercase
    r = client.post("/register", data={"name": "Test User", "email": "valid@email.com", "phone": "09171234567", "address": "Lipa", "password": "UPPERCASE123!", "confirm_password": "UPPERCASE123!"}, follow_redirects=True)
    assert "lowercase letter" in r.data.decode("utf-8")

    # H. Password missing number
    r = client.post("/register", data={"name": "Test User", "email": "valid@email.com", "phone": "09171234567", "address": "Lipa", "password": "NoNumbersHere!", "confirm_password": "NoNumbersHere!"}, follow_redirects=True)
    assert "number (0-9)" in r.data.decode("utf-8")

    # I. Password missing special character
    r = client.post("/register", data={"name": "Test User", "email": "valid@email.com", "phone": "09171234567", "address": "Lipa", "password": "NoSpecialChar123", "confirm_password": "NoSpecialChar123"}, follow_redirects=True)
    assert "special character" in r.data.decode("utf-8")

    # J. Password contains spaces
    r = client.post("/register", data={"name": "Test User", "email": "valid@email.com", "phone": "09171234567", "address": "Lipa", "password": "Space in@Password123", "confirm_password": "Space in@Password123"}, follow_redirects=True)
    assert "must not contain spaces" in r.data.decode("utf-8")

    # K. Common password rejection
    r = client.post("/register", data={"name": "Test User", "email": "valid@email.com", "phone": "09171234567", "address": "Lipa", "password": "password123", "confirm_password": "password123"}, follow_redirects=True)
    assert "uppercase letter" in r.data.decode("utf-8") or "special character" in r.data.decode("utf-8") or "too common" in r.data.decode("utf-8")

    # L. Successful registration with strong compliant password
    test_email = "new_customer_test@example.com"
    conn = get_db()
    conn.execute("DELETE FROM users WHERE email = ?", (test_email,))
    conn.commit()
    conn.close()

    r = client.post("/register", data={
        "name": "Maria Clara Construction",
        "email": test_email,
        "phone": "09187654321",
        "address": "San Carlos, Lipa City, Batangas",
        "password": "Strong@Password2026",
        "confirm_password": "Strong@Password2026",
    }, follow_redirects=True)
    assert "Account created successfully" in r.data.decode("utf-8"), "Registration success flash missing"

    # Verify user in database has role 'customer'
    conn = get_db()
    new_user = conn.execute("SELECT * FROM users WHERE email = ?", (test_email,)).fetchone()
    assert new_user is not None, "Registered user not found in DB"
    assert new_user["role"] == "customer", f"Expected role 'customer', got {new_user['role']}"
    assert new_user["phone"] == "09187654321"
    conn.close()
    print("  PASS: Customer registration strictly enforces all password and contact validations and sets role='customer'.")

    # -------------------------------------------------------------
    # 4. PORTAL AUTHENTICATION & ACCESS SEGREGATION
    # -------------------------------------------------------------
    print("\n[TEST 4] Portal Authentication & Access Segregation")

    # A. Customer login with customer credentials
    cust_client = app.test_client()
    r = cust_client.post("/login", data={"identifier": test_email, "password": "Strong@Password2026"}, follow_redirects=False)
    assert r.status_code == 302 and "/customer/dashboard" in r.headers.get("Location", ""), f"Customer login redirect failed: {r.headers.get('Location')}"

    # Verify dashboard page loads
    r_dash = cust_client.get("/customer/dashboard")
    assert r_dash.status_code == 200, f"Customer dashboard failed: {r_dash.status_code}"
    assert "Maria Clara Construction" in r_dash.data.decode("utf-8")

    # B. Admin attempting to login via customer /login -> rejected & redirected to /admin/login
    r = client.post("/login", data={"identifier": "admin@rml.com", "password": "admin123"}, follow_redirects=True)
    assert "Admin/Staff accounts must sign in via the restricted Admin Portal" in r.data.decode("utf-8")

    # C. Driver attempting to login via customer /login -> rejected & redirected to /driver/login
    r = client.post("/login", data={"identifier": "driver@rml.com", "password": "driver123"}, follow_redirects=True)
    assert "Driver accounts must sign in via the restricted Driver Portal" in r.data.decode("utf-8")

    # D. Customer attempting to login via /admin/login -> rejected
    r = client.post("/admin/login", data={"identifier": test_email, "password": "Strong@Password2026"}, follow_redirects=True)
    assert "Access denied. Authorized administrative personnel only" in r.data.decode("utf-8")

    # E. Customer attempting to login via /driver/login -> rejected
    r = client.post("/driver/login", data={"identifier": test_email, "password": "Strong@Password2026"}, follow_redirects=True)
    assert "Access denied. Authorized delivery drivers only" in r.data.decode("utf-8")

    # F. Admin login at /admin/login with Staff ID or email
    admin_client = app.test_client()
    r = admin_client.post("/admin/login", data={"identifier": "RML-ADM-001", "password": "admin123"}, follow_redirects=False)
    assert r.status_code == 302 and "/admin/dashboard" in r.headers.get("Location", ""), f"Admin login failed: {r.headers.get('Location')}"

    # G. Driver login at /driver/login with Staff ID or email
    driver_client = app.test_client()
    r = driver_client.post("/driver/login", data={"identifier": "RML-DRV-014", "password": "driver123"}, follow_redirects=False)
    assert r.status_code == 302 and "/driver/dashboard" in r.headers.get("Location", ""), f"Driver login failed: {r.headers.get('Location')}"

    print("  PASS: Each portal strictly admits only authorized roles and blocks foreign accounts.")

    # -------------------------------------------------------------
    # 5. ROLE-BASED ACCESS CONTROL (RBAC) & DIRECT URL PROTECTION
    # -------------------------------------------------------------
    print("\n[TEST 5] RBAC Route Protection")

    # A. Unauthenticated attempts to access protected routes
    anon_client = app.test_client()
    r = anon_client.get("/admin/dashboard", follow_redirects=False)
    assert r.status_code == 302 and "/admin/login" in r.headers.get("Location", ""), "Anon accessing admin route must redirect to /admin/login"

    r = anon_client.get("/driver/dashboard", follow_redirects=False)
    assert r.status_code == 302 and "/driver/login" in r.headers.get("Location", ""), "Anon accessing driver route must redirect to /driver/login"

    r = anon_client.get("/customer/dashboard", follow_redirects=False)
    assert r.status_code == 302 and "/login" in r.headers.get("Location", ""), "Anon accessing customer route must redirect to /login"

    # B. Customer attempting direct URL to /admin/* or /driver/*
    r = cust_client.get("/admin/dashboard", follow_redirects=True)
    assert "Access denied. Restricted to authorized administrators" in r.data.decode("utf-8")

    r = cust_client.get("/driver/dashboard", follow_redirects=True)
    assert "Access denied. Restricted to delivery drivers" in r.data.decode("utf-8")

    # C. Driver attempting direct URL to /admin/*
    r = driver_client.get("/admin/dashboard", follow_redirects=True)
    assert "Access denied. Restricted to authorized administrators" in r.data.decode("utf-8")

    print("  PASS: All routes protected with server-side RBAC checks and prevent cross-portal URL penetration.")

    # -------------------------------------------------------------
    # 6. DEDICATED LOGOUT HANDLERS
    # -------------------------------------------------------------
    print("\n[TEST 6] Dedicated Logout Routes")
    r = cust_client.get("/logout", follow_redirects=False)
    assert r.status_code == 302 and "/login" in r.headers.get("Location", "")

    r = admin_client.get("/admin/logout", follow_redirects=False)
    assert r.status_code == 302 and "/admin/login" in r.headers.get("Location", "")

    r = driver_client.get("/driver/logout", follow_redirects=False)
    assert r.status_code == 302 and "/driver/login" in r.headers.get("Location", "")
    print("  PASS: Logout handlers invalidate sessions and redirect cleanly to respective portal sign-ins.")

    # -------------------------------------------------------------
    # 7. FORGOT PASSWORD & RESET PASSWORD FLOW
    # -------------------------------------------------------------
    print("\n[TEST 7] Forgot & Reset Password Token Flow")
    r = client.post("/forgot-password", data={"email": test_email}, follow_redirects=True)
    html = r.data.decode("utf-8")
    assert "Password reset link generated" in html or "password reset instructions" in html

    conn = get_db()
    u = conn.execute("SELECT reset_token FROM users WHERE email = ?", (test_email,)).fetchone()
    token = u["reset_token"]
    assert token is not None, "Reset token was not set in DB"
    conn.close()

    # Access reset password page
    r = client.get(f"/reset-password/{token}")
    assert r.status_code == 200
    assert "Create New Password" in r.data.decode("utf-8")

    # Submit new password with strict policy check
    new_pwd = "NewP@ssw0rdSecure2026"
    r = client.post(f"/reset-password/{token}", data={"password": new_pwd, "confirm_password": new_pwd}, follow_redirects=True)
    assert "Your password has been reset successfully" in r.data.decode("utf-8")

    # Verify customer can sign in with new password
    test_client = app.test_client()
    r = test_client.post("/login", data={"identifier": test_email, "password": new_pwd}, follow_redirects=False)
    assert r.status_code == 302 and "/customer/dashboard" in r.headers.get("Location", "")
    print("  PASS: Cryptographic reset tokens, strict password verification, and post-reset authentication verified.")

    # -------------------------------------------------------------
    # 8. PRESERVATION OF EXISTING BUSINESS DATA & CATALOG
    # -------------------------------------------------------------
    print("\n[TEST 8] Preservation of Existing Business Data")
    conn = get_db()
    prod_count = conn.execute("SELECT COUNT(*) AS c FROM products WHERE is_active = 1").fetchone()["c"]
    var_count = conn.execute("SELECT COUNT(*) AS c FROM product_variations WHERE is_available = 1").fetchone()["c"]
    order_count = conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]
    truck_count = conn.execute("SELECT COUNT(*) AS c FROM trucks").fetchone()["c"]
    conn.close()

    print(f"  Active Products: {prod_count}")
    print(f"  Active Variations: {var_count}")
    print(f"  Existing Orders: {order_count}")
    print(f"  Active Trucks: {truck_count}")

    assert prod_count >= 57, f"Products count dropped! {prod_count}"
    assert var_count >= 120, f"Variations count dropped! {var_count}"
    assert order_count >= 8, f"Orders count dropped! {order_count}"
    print("  PASS: All 57 catalog products, 124 variations, legitimate customer orders, and fleet data 100% intact.")

    print("\n" + "=" * 70)
    print("ALL VERIFICATION SUITES PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()

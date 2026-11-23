import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from app import app
from db import get_db

with app.test_client() as c:
    print("--- 1. Testing Registration HTML Elements ---")
    res = c.get("/register")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # 1. No permanent checklist or gray container
    assert "strengthBar" not in html, "ERROR: strengthBar still in HTML"
    assert "strengthLabel" not in html, "ERROR: strengthLabel still in HTML"
    assert 'id="ruleLength"' not in html, "ERROR: ruleLength still in HTML"
    assert 'id="ruleUpper"' not in html, "ERROR: ruleUpper still in HTML"
    assert 'id="ruleSpecial"' not in html, "ERROR: ruleSpecial still in HTML"
    assert '<div class="card bg-light border p-2 mb-2 rounded-2">' not in html, "ERROR: old requirements card still in HTML"
    print("PASS: Permanently visible checklist and gray container completely removed.")

    # 2. Contains subtle helper container
    assert 'id="passwordHelper"' in html
    assert "Use at least 8 characters with uppercase, lowercase, a number, and a special character." in html
    print("PASS: Subtle passwordHelper exists with single helper sentence initially.")

    # 3. Contains show/hide toggle buttons
    assert "togglePassword('regPassword', this)" in html
    assert "togglePassword('regConfirmPassword', this)" in html
    print("PASS: Show/Hide eye buttons present for both password fields.")

    # 4. Helper message text present in JS logic
    assert "Password must be at least 8 characters and include uppercase, lowercase, a number, and a special character." in html
    assert "Password meets all requirements." in html
    print("PASS: Exact prompt helper messages present in real-time validation script.")

    print("\n--- 2. Testing Strict Backend Password Validation (All 6 Rules) ---")
    
    # Missing uppercase
    r = c.post("/register", data={
        "name": "Test Builder",
        "email": "testbuilder@example.com",
        "phone": "09171112233",
        "address": "Lipa City",
        "password": "password123!",
        "confirm_password": "password123!"
    }, follow_redirects=True)
    assert "uppercase letter" in r.get_data(as_text=True)
    print("PASS: Rejects password missing uppercase.")

    # Missing lowercase
    r = c.post("/register", data={
        "name": "Test Builder",
        "email": "testbuilder@example.com",
        "phone": "09171112233",
        "address": "Lipa City",
        "password": "PASSWORD123!",
        "confirm_password": "PASSWORD123!"
    }, follow_redirects=True)
    assert "lowercase letter" in r.get_data(as_text=True)
    print("PASS: Rejects password missing lowercase.")

    # Missing number
    r = c.post("/register", data={
        "name": "Test Builder",
        "email": "testbuilder@example.com",
        "phone": "09171112233",
        "address": "Lipa City",
        "password": "Password!Special",
        "confirm_password": "Password!Special"
    }, follow_redirects=True)
    assert "number (0-9)" in r.get_data(as_text=True)
    print("PASS: Rejects password missing number.")

    # Missing special character
    r = c.post("/register", data={
        "name": "Test Builder",
        "email": "testbuilder@example.com",
        "phone": "09171112233",
        "address": "Lipa City",
        "password": "Password12345",
        "confirm_password": "Password12345"
    }, follow_redirects=True)
    assert "special character" in r.get_data(as_text=True)
    print("PASS: Rejects password missing special character.")

    # Length < 8
    r = c.post("/register", data={
        "name": "Test Builder",
        "email": "testbuilder@example.com",
        "phone": "09171112233",
        "address": "Lipa City",
        "password": "Sh0rt!",
        "confirm_password": "Sh0rt!"
    }, follow_redirects=True)
    assert "at least 8 characters" in r.get_data(as_text=True)
    print("PASS: Rejects password shorter than 8 characters.")

    # Contains spaces
    r = c.post("/register", data={
        "name": "Test Builder",
        "email": "testbuilder@example.com",
        "phone": "09171112233",
        "address": "Lipa City",
        "password": "Space in@Password123",
        "confirm_password": "Space in@Password123"
    }, follow_redirects=True)
    assert "must not contain spaces" in r.get_data(as_text=True)
    print("PASS: Rejects password containing spaces.")

    # Password confirmation mismatch
    r = c.post("/register", data={
        "name": "Test Builder",
        "email": "testbuilder@example.com",
        "phone": "09171112233",
        "address": "Lipa City",
        "password": "Valid@Password2026",
        "confirm_password": "DifferentPassword@2026"
    }, follow_redirects=True)
    assert "Passwords do not match" in r.get_data(as_text=True)
    print("PASS: Rejects password confirmation mismatch.")

    # Successful registration with fully compliant password
    clean_email = "minimalist_pwd_test@example.com"
    conn = get_db()
    conn.execute("DELETE FROM users WHERE email = ?", (clean_email,))
    conn.commit()
    conn.close()

    r = c.post("/register", data={
        "name": "Clean Test User",
        "email": clean_email,
        "phone": "09179998877",
        "address": "Barangay Marawoy, Lipa City, Batangas",
        "password": "SecurePassword#2026",
        "confirm_password": "SecurePassword#2026"
    }, follow_redirects=True)
    assert r.status_code == 200
    res_text = r.get_data(as_text=True)
    assert "Account created successfully" in res_text or "Customer Portal" in res_text
    print("PASS: Valid password registers successfully and directs to customer portal.")

    # Cleanup test user
    conn = get_db()
    conn.execute("DELETE FROM users WHERE email = ?", (clean_email,))
    conn.commit()
    conn.close()
    print("PASS: Test user cleaned up.")

print("\n=======================================================")
print("ALL PASSWORD UX REDESIGN TESTS PASSED WITH 100% SUCCESS!")
print("=======================================================")

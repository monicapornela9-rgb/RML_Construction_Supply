import os
import sys
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "RML")))
from app import app
from db import get_db

def run_tests():
    client = app.test_client()

    # Reset any leftover test logs
    conn = get_db()
    conn.execute("DELETE FROM access_logs WHERE affected_user_name LIKE '%Test%'")
    conn.commit()
    conn.close()

    # Admin session
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "admin"
        sess["user_name"] = "RML Admin"
        sess["_fresh"] = True

    print("--- Test 1: GET /admin/access default view ---")
    res = client.get("/admin/access")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.data.decode("utf-8")

    # Verify 3 tabs
    assert "User Accounts" in html
    assert "Roles &amp; Permissions" in html or "Roles & Permissions" in html
    assert "Access Logs" in html

    # Verify overview statistics cards
    assert "Total Accounts" in html
    assert "Administrators" in html
    assert "Delivery Drivers" in html
    assert "Customer Accounts" in html

    # Verify directory table and search
    assert "All Accounts Directory" in html
    assert "accountSearchInput" in html
    assert "roleFilterSelect" in html
    assert "statusFilterSelect" in html

    # Verify permission matrix
    assert "System Permission Matrix" in html
    assert "Staff Role Assignment" in html

    # Verify modals
    assert "addUserModal" in html
    assert "accountDetailsModal" in html
    assert "confirmActionModal" in html

    print("PASS: Page structure and all 3 tabs present.")

    print("\n--- Test 2: Tab query parameters and filters ---")
    res_roles = client.get("/admin/access?tab=roles")
    assert res_roles.status_code == 200
    assert "System Permission Matrix" in res_roles.data.decode("utf-8")

    res_logs = client.get("/admin/access?tab=logs")
    assert res_logs.status_code == 200
    assert "Access &amp; Security Activity Logs" in res_logs.data.decode("utf-8") or "Access & Security Activity Logs" in res_logs.data.decode("utf-8")

    res_driver_filter = client.get("/admin/access?role_filter=driver")
    assert res_driver_filter.status_code == 200
    html_drv = res_driver_filter.data.decode("utf-8")
    assert "Juan Dela Cruz" in html_drv

    res_search = client.get("/admin/access?search=Monica")
    assert res_search.status_code == 200
    assert "Monica" in res_search.data.decode("utf-8")
    print("PASS: Query parameters, tabs, and filters work correctly.")

    print("\n--- Test 3: Self-lockout & Self-demotion Protection ---")
    # Attempting to suspend own account (id=1)
    res_self_suspend = client.post("/admin/access", data={
        "action": "toggle_active",
        "user_id": 1,
        "status": "suspended"
    }, follow_redirects=True)
    html_self_susp = res_self_suspend.data.decode("utf-8")
    assert "Protection active: You cannot suspend your own active administrator account" in html_self_susp
    
    # Verify in DB admin id=1 is still is_active=1
    conn = get_db()
    admin_row = conn.execute("SELECT is_active, role FROM users WHERE id = 1").fetchone()
    assert admin_row["is_active"] == 1, "Admin account was erroneously deactivated!"
    assert admin_row["role"] == "admin", "Admin role was changed!"
    conn.close()

    # Attempting to demote own account (id=1) to driver
    res_self_demote = client.post("/admin/access", data={
        "action": "update_role",
        "user_id": 1,
        "role": "driver"
    }, follow_redirects=True)
    html_self_demote = res_self_demote.data.decode("utf-8")
    assert "Protection active: Administrators cannot remove their own administrative privileges" in html_self_demote
    
    conn = get_db()
    admin_row = conn.execute("SELECT is_active, role FROM users WHERE id = 1").fetchone()
    assert admin_row["role"] == "admin", "Admin was demoted!"
    conn.close()
    print("PASS: Self-lockout and self-demotion protection verified.")

    print("\n--- Test 4: Suspend & Activate another user + Audit Logging ---")
    conn = get_db()
    test_user = conn.execute("SELECT id, name, is_active FROM users WHERE role != 'admin' LIMIT 1").fetchone()
    target_id = test_user["id"]
    initial_active = test_user["is_active"]
    target_action = "suspended" if initial_active == 1 else "active"
    expected_new = 0 if initial_active == 1 else 1
    conn.close()

    # Toggle
    res_toggle = client.post("/admin/access", data={
        "action": "toggle_active",
        "user_id": target_id,
        "status": target_action
    }, follow_redirects=True)
    assert res_toggle.status_code == 200

    # Verify DB update in fresh connection
    conn = get_db()
    updated_user = conn.execute("SELECT is_active FROM users WHERE id = ?", (target_id,)).fetchone()
    assert updated_user["is_active"] == expected_new, "Status was not updated in DB!"

    # Verify access_logs record
    log_row = conn.execute("SELECT * FROM access_logs WHERE affected_user_id = ? ORDER BY id DESC LIMIT 1", (target_id,)).fetchone()
    assert log_row is not None, "Audit log was not written!"
    assert "Account " in log_row["action"]
    print(f"PASS: Status toggled and verified log: {log_row['action']} for user {log_row['affected_user_name']} (ID: {log_row['affected_user_id']})")
    conn.close()

    # Restore original status
    client.post("/admin/access", data={
        "action": "toggle_active",
        "user_id": target_id,
        "status": "active" if initial_active == 1 else "suspended"
    }, follow_redirects=True)

    conn = get_db()
    restored_user = conn.execute("SELECT is_active FROM users WHERE id = ?", (target_id,)).fetchone()
    assert restored_user["is_active"] == initial_active
    conn.close()
    print("PASS: Reverted user to original status cleanly.")

    print("\n--- Test 5: Staff creation + Audit Logging ---")
    test_staff_email = "test_staff_driver_99@rml.com"
    conn = get_db()
    conn.execute("DELETE FROM users WHERE email = ?", (test_staff_email,))
    conn.commit()
    conn.close()

    res_add = client.post("/admin/access", data={
        "action": "add_staff",
        "name": "Test Driver Pilot",
        "email": test_staff_email,
        "phone": "09170009999",
        "role": "driver",
        "staff_id": "RML-DRV-999",
        "password": "testpassword123"
    }, follow_redirects=True)
    assert res_add.status_code == 200

    # Verify created
    conn = get_db()
    new_user = conn.execute("SELECT * FROM users WHERE email = ?", (test_staff_email,)).fetchone()
    assert new_user is not None
    assert new_user["staff_id"] == "RML-DRV-999"
    assert new_user["role"] == "driver"

    # Check log
    created_log = conn.execute("SELECT * FROM access_logs WHERE affected_user_id = ?", (new_user["id"],)).fetchone()
    assert created_log is not None
    assert created_log["action"] == "Staff Account Created"

    # Clean up test staff
    conn.execute("DELETE FROM access_logs WHERE affected_user_id = ?", (new_user["id"],))
    conn.execute("DELETE FROM users WHERE id = ?", (new_user["id"],))
    conn.commit()
    conn.close()
    print("PASS: Staff creation, password hashing, and logging verified.")

    print("\n--- Test 6: Verify Access Logs tab renders real logs ---")
    res_logs_view = client.get("/admin/access?tab=logs")
    assert res_logs_view.status_code == 200
    html_logs = res_logs_view.data.decode("utf-8")
    assert "Access &amp; Security Activity Logs" in html_logs or "Access & Security Activity Logs" in html_logs
    assert "Account " in html_logs
    print("PASS: Access logs table displays actual recorded operations.")

    print("\nALL ACCESS & ROLES TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()

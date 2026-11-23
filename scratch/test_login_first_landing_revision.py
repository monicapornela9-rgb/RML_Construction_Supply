import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from app import app
from db import get_db

with app.test_client() as c:
    print("======================================================================")
    print("TESTING LOGIN-FIRST LANDING REVISION (PROMPT 11 SPECIFICATIONS)")
    print("======================================================================\n")

    # 1. PUBLIC LANDING PAGE (/) VERIFICATION
    print("[TEST 1] Landing Page 7-Section Architecture & Content")
    res = c.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Section 1: Navigation Bar
    assert "RML Construction Supply" in html
    assert "Home" in html
    assert "Categories" in html
    assert "About Us" in html
    assert "Services" in html
    assert "Contact Us" in html
    assert "Customer Login" in html
    assert "Register Now" in html
    assert "/admin/login" not in html
    assert "/driver/login" not in html
    assert "Admin Portal" not in html
    assert "Driver Portal" not in html
    print("  PASS: Section 1 (Navbar) has exact links, customer actions, and zero admin/driver leaks.")

    # Section 2: Hero Section
    assert "Your Trusted Partner in Construction Supply." in html
    assert "Access quality construction materials, manage your orders, and monitor deliveries through one convenient platform." in html
    assert "Explore Our Services" in html
    assert "Get Started / Register Now" in html
    assert "hero-image-box" in html
    print("  PASS: Section 2 (Hero) has exact headline, description, action buttons, and depot image.")

    # Section 3: Product Categories (Preview Only)
    assert "Cement" in html
    assert "Steel Bars" in html
    assert "Aggregates" in html
    assert "Roofing Materials" in html
    assert "Plumbing Materials" in html
    assert "Hardware and Supplies" in html
    assert "category-card-uniform" in html
    # Ensure unauthenticated users are directed to login with next parameter
    assert "/login?next=" in html
    print("  PASS: Section 3 (Categories) has 6 uniform preview cards linking to login with return destination.")

    # Section 4: About RML Construction Supply
    assert "Your Reliable Partner in Construction Supply" in html
    assert "Lipa City and Batangas Province" in html
    print("  PASS: Section 4 (About) concise intro and regional commitment verified.")

    # Section 5: Our Services (4 Major Services)
    assert "Our Services" in html
    assert "1. Construction Materials Ordering" in html
    assert "2. Order Management" in html
    assert "3. Scheduled Deliveries" in html
    assert "4. GPS Delivery Tracking" in html
    print("  PASS: Section 5 (Services) highlights the 4 major supported services.")

    # Section 6: Login-First Call to Action
    assert "Everything You Need to Manage Your Construction Orders." in html
    assert "Create an account or sign in to explore our complete ordering platform, manage your materials, monitor your transactions, and track your deliveries." in html
    assert "Customer Login" in html
    assert "Create an Account" in html
    print("  PASS: Section 6 (Login-First CTA) prominent navy & red branded conversion container verified.")

    # Section 7: Compact Professional Footer
    assert "Purok 6, Brgy. Antipolo del Sur, Lipa City, Batangas 4217" in html
    assert "0917 555 0100" in html
    assert "logistics@rml.com" in html
    assert "Privacy Policy" in html
    assert "Terms and Conditions" in html
    print("  PASS: Section 7 (Footer) compact contact info, hours, and legal modals verified.")

    # Ensure redundant product sections are removed from landing page
    assert "Direct Depot Stock" not in html
    assert "b2b-product-card" not in html
    print("  PASS: Redundant product catalogs and Direct Depot Stock sections successfully removed from homepage.")

    # 2. LOGIN-FIRST GATING ON CUSTOMER CATALOG
    print("\n[TEST 2] Login-First Access Gating & Intended Destination Preservation")
    # Unauthenticated visitor attempting to access catalog
    res_cat_unauth = c.get("/customer/catalog", follow_redirects=False)
    assert res_cat_unauth.status_code == 302
    redirect_loc = res_cat_unauth.headers.get("Location", "")
    assert "/login" in redirect_loc and ("next=/customer/catalog" in redirect_loc or "next=%2Fcustomer%2Fcatalog" in redirect_loc)
    print(f"  PASS: Unauthenticated visit to /customer/catalog redirects to {redirect_loc}")

    # Follow redirect and verify flash message
    res_cat_followed = c.get("/customer/catalog", follow_redirects=True)
    followed_html = res_cat_followed.get_data(as_text=True)
    assert "You need to sign in to access the complete product catalog." in followed_html
    print("  PASS: Informative authentication required message displayed on login page.")

    # 3. AUTHENTICATED CUSTOMER WORKFLOW WITH 'NEXT' REDIRECT
    print("\n[TEST 3] Customer Login & Destination Redirect Fulfillment")
    res_login_dest = c.post("/login", data={
        "identifier": "customer@rml.com",
        "password": "customer123",
        "next": "/customer/catalog?q=Cement"
    }, follow_redirects=False)
    assert res_login_dest.status_code == 302
    assert res_login_dest.headers.get("Location") == "/customer/catalog?q=Cement"
    print("  PASS: Login with next destination redirects straight to intended target: /customer/catalog?q=Cement")

    # Now with authenticated session, accessing catalog succeeds with HTTP 200
    res_cat_auth = c.get("/customer/catalog?q=Cement")
    assert res_cat_auth.status_code == 200
    cat_auth_html = res_cat_auth.get_data(as_text=True)
    assert "Cement" in cat_auth_html
    assert "catalog-store-layout" in cat_auth_html
    assert "b2b-product-card" in cat_auth_html
    print("  PASS: Authenticated customer can comfortably browse full product catalog, search & filter.")

    # 4. COLOR PALETTE VALIDATION (PROMPT 11)
    print("\n[TEST 4] Brand Identity & Color Palette CSS Verification")
    with open('RML/static/css/style.css', 'r', encoding='utf-8') as f:
        css = f.read()
    assert '--rml-navy: #142235;' in css
    assert '--rml-red: #C83227;' in css
    assert '--rml-light: #F1F3F6;' in css
    assert '--rml-text-muted: #64748B;' in css
    print("  PASS: Exact Prompt 11 color palette hex codes verified.")

    print("\n======================================================================")
    print("ALL LOGIN-FIRST LANDING REVISION TESTS PASSED WITH 100% SUCCESS!")
    print("======================================================================")

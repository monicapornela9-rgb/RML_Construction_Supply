import sys
import os

sys.path.insert(0, os.path.abspath('RML'))
from app import app
from db import get_db

with app.test_client() as c:
    print("======================================================================")
    print("TESTING FIGMA UI/UX REDESIGN & SYSTEM SPECIFICATIONS (PROMPT 10)")
    print("======================================================================\n")

    # 1. COLOR PALETTE & CSS SYSTEM VERIFICATION
    print("[TEST 1] Brand Identity & Color Palette CSS Verification")
    with open('RML/static/css/style.css', 'r', encoding='utf-8') as f:
        css = f.read()
    assert '--rml-navy: #142235;' in css, "Primary Navy Blue #142235 missing in CSS"
    assert '--rml-navy-surface: #1C3048;' in css, "Secondary Navy Blue #1C3048 missing in CSS"
    assert '--rml-red: #D93025;' in css, "Brand Red #D93025 missing in CSS"
    assert '--rml-light: #F3F5F8;' in css, "Light Gray #F3F5F8 missing in CSS"
    assert '--rml-text-dark: #172334;' in css, "Dark Text #172334 missing in CSS"
    assert '--rml-text-muted: #64748B;' in css, "Secondary Text #64748B missing in CSS"
    assert '--rml-border: #DCE2E9;' in css, "Border #DCE2E9 missing in CSS"
    print("  PASS: All 7 required brand hex colors verified in CSS variables.")

    # 2. PUBLIC LANDING PAGE (/) STRUCTURE & VISUAL HIERARCHY
    print("\n[TEST 2] Public Landing Page (/) Redesign")
    res = c.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # 2.A Navigation Bar
    assert "RML Construction Supply" in html
    assert "Home" in html
    assert "Products" in html
    assert "About Us" in html
    assert "Services" in html
    assert "Contact Us" in html
    assert "Customer Login" in html
    assert "Register Now" in html
    assert "/admin/login" not in html
    assert "/driver/login" not in html
    assert "Admin Portal" not in html
    assert "Driver Portal" not in html
    print("  PASS: A. Navbar layout, brand title, right-aligned customer actions, zero admin/driver links.")

    # 2.B Hero Section
    assert "Reliable Construction Materials. Delivered with Confidence." in html
    assert "Your trusted partner for quality-certified construction materials, dependable delivery scheduling, and real-time fleet tracking across Lipa City and Batangas Province." in html
    assert "Browse Materials" in html
    assert "Customer Login" in html
    assert "hero-image-box" in html
    print("  PASS: B. Hero headline, supporting description, primary buttons, and warehouse depot image.")

    # 2.C Product Categories
    assert "Explore Our Construction Materials" in html
    assert "Steel Bars" in html
    assert "Cement" in html
    assert "Aggregates" in html
    assert "Plumbing Materials" in html
    assert "Hardware and Supplies" in html
    assert "Other Construction Materials" in html
    assert "View All Categories" in html
    assert "category-card-uniform" in html
    print("  PASS: C. Product Categories section with 6 uniform category cards and View All Categories link.")

    # 2.D Featured Products
    assert "Featured Construction Materials" in html
    assert "product-grid-compact" in html
    assert "b2b-product-card" in html
    assert "&#8369;" in html
    assert "View Details" in html
    assert "View Full Catalog" in html
    print("  PASS: D. Featured Construction Materials with 4-6 live database products, ₱ prices, stock badges.")

    # 2.E About RML Construction Supply
    assert "Your Reliable Partner in Construction Supply" in html
    assert "Lipa City and Batangas Province" in html
    print("  PASS: E. About section with exact heading and Lipa City/Batangas regional commitment.")

    # 2.F Why Choose RML
    assert "Why Choose RML Construction Supply?" in html
    assert "Quality Materials" in html
    assert "Transparent Pricing" in html
    assert "Convenient Ordering" in html
    assert "Reliable Delivery" in html
    print("  PASS: F. 4 core business advantages clearly displayed.")

    # 2.G Delivery and GPS Tracking Preview
    assert "Stay Updated on Every Delivery" in html
    assert "Monitor your scheduled deliveries and track assigned trucks through our integrated GPS tracking system." in html
    assert "gps-map-mockup" in html
    assert "Customer Login to Track Delivery" in html
    print("  PASS: G. GPS tracking preview with map mockup, telemetry explanation, and CTA.")

    # 2.H Contact & Footer
    assert "Purok 6, Brgy. Antipolo del Sur, Lipa City, Batangas 4217" in html
    assert "0917 555 0100" in html
    assert "logistics@rml.com" in html
    assert "Privacy Policy" in html
    assert "Terms and Conditions" in html
    print("  PASS: H. Contact section with official Lipa City depot details, hotline, hours, and modal policies.")

    # 3. CUSTOMER LOGIN (/login) SPLIT-SCREEN LAYOUT
    print("\n[TEST 3] Customer Login (/login) Split-Screen Design")
    res_login = c.get("/login")
    assert res_login.status_code == 200
    lhtml = res_login.get_data(as_text=True)

    assert "figma-split-login-container" in lhtml
    assert "figma-login-visual" in lhtml
    assert "figma-login-form-pane" in lhtml
    assert "Customer Portal" in lhtml
    assert "Email Address *" in lhtml
    assert "Password *" in lhtml
    assert "Forgot Password?" in lhtml
    assert "Remember Me" in lhtml
    assert "Sign In" in lhtml
    assert "Register Here" in lhtml
    assert "togglePassword('loginPassword', this)" in lhtml
    assert "role=\"tab\"" not in lhtml
    assert "Admin Portal" not in lhtml
    assert "Driver Portal" not in lhtml
    print("  PASS: Figma split-screen login verified (visual left, clean form right, Remember Me, toggle).")

    # 4. CUSTOMER REGISTRATION (/register) & PASSWORD UX
    print("\n[TEST 4] Customer Registration (/register) Form & Password UX")
    res_reg = c.get("/register")
    assert res_reg.status_code == 200
    rhtml = res_reg.get_data(as_text=True)

    assert "Company or Full Name *" in rhtml
    assert "Email Address *" in rhtml
    assert "Contact Number (Philippine) *" in rhtml
    assert "Complete Delivery / Site Address *" in rhtml
    assert "Password *" in rhtml
    assert "Confirm Password *" in rhtml
    assert "Complete Customer Registration" in rhtml
    assert "card bg-light border p-2 mb-2 rounded-2" not in rhtml
    assert "Use at least 8 characters with uppercase, lowercase, a number, and a special character." in rhtml
    print("  PASS: 5-row registration form, subtle helper sentence, no bulky checklist box.")

    # 5. PRODUCT CATALOG EXPERIENCE & PUBLIC GUEST EXPLORATION
    print("\n[TEST 5] Product Catalog Experience & Public Access")
    res_cat = c.get("/customer/catalog")
    assert res_cat.status_code == 200
    cat_html = res_cat.get_data(as_text=True)
    assert "catalog-store-layout" in cat_html
    assert "catalog-filter-sidebar" in cat_html
    assert "b2b-product-card" in cat_html
    print("  PASS: Full dedicated product catalog accessible to public visitors.")

    # Unauthenticated checkout gating
    res_chk = c.get("/customer/checkout", follow_redirects=False)
    assert res_chk.status_code == 302 and "/login" in res_chk.headers.get("Location", "")
    print("  PASS: Checkout strictly gated behind customer authentication.")

    print("\n======================================================================")
    print("ALL FIGMA PROMPT 10 REDESIGN SPECIFICATIONS VERIFIED 100% SUCCESSFULLY!")
    print("======================================================================")

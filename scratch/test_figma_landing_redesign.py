import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'RML')))
from app import app

class FigmaLandingRedesignTest(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_01_landing_page_renders_all_9_figma_sections(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')

        # 1. Wrapper
        self.assertIn('figma-landing-wrapper', html)

        # 2. Section 1 - Navigation
        self.assertIn('figma-landing-nav', html)
        self.assertIn('RML Construction Supply', html)
        self.assertIn('Materials', html)
        self.assertIn('About RML', html)
        self.assertIn('Service areas', html)
        self.assertIn('Customer login', html)

        # 3. Section 2 - Hero
        self.assertIn('figma-landing-hero', html)
        self.assertIn('LIPA CITY, BATANGAS', html)
        self.assertIn('Cement, Steel Bars, Yero, and Plywood – Marine — delivered across Lipa City, Batangas.', html)
        self.assertIn('Browse Materials', html)
        self.assertIn('Get a Quote', html)
        self.assertIn('landing_steel_bars.png', html)

        # 4. Section 3 - Shop by Category (4 categories)
        self.assertIn('Shop by Category', html)
        self.assertIn('Choose what you need and request delivery in minutes.', html)
        self.assertIn('Cement', html)
        self.assertIn('Steel Bars', html)
        self.assertIn('Yero', html)
        self.assertIn('Plywood – Marine', html)
        self.assertIn('landing_cement.png', html)
        self.assertIn('landing_roofing.png', html)
        self.assertIn('landing_plywood.png', html)

        # 5. Section 4 - About RML
        self.assertIn('About RML', html)
        self.assertIn('Local supply, dependable delivery, and transparent transactions.', html)
        self.assertIn('RML Construction Supply &middot; Lipa &bull; Batangas', html)

        # 6. Section 5 - How ordering works (3 steps)
        self.assertIn('From your materials list to your site', html)
        self.assertIn('Choose materials', html)
        self.assertIn('Review your order', html)
        self.assertIn('Pay and track', html)
        self.assertIn('01', html)
        self.assertIn('02', html)
        self.assertIn('03', html)

        # 7. Section 6 - Service Areas & Contact Details
        self.assertIn('Service Areas &amp; Contact Details', html)
        self.assertIn('Lipa City, Batangas', html)
        self.assertIn('Batangas Province', html)
        self.assertIn('Contact RML for a quote', html)

        # 8. Section 7 - Customer Access (Login-First)
        self.assertIn('Customer Login / Sign Up', html)
        self.assertIn('Your project, in one place', html)
        self.assertIn('Ready to get started?', html)
        self.assertIn('Continue to customer sign-in &rarr;', html)

        # 9. Section 8 - Customer Feedback
        self.assertIn('Customer Feedback', html)
        self.assertIn('Marian S.', html)
        self.assertIn('Eugene R.', html)
        self.assertIn('Kaye L.', html)

        # 10. Section 9 - Footer
        self.assertIn('figma-landing-footer', html)
        self.assertIn('RML Construction Supply &bull; Lipa, Batangas', html)
        self.assertIn('privacyModal', html)
        self.assertIn('termsModal', html)

    def test_02_landing_image_assets_accessible(self):
        images = [
            'landing_steel_bars.png',
            'landing_cement.png',
            'landing_roofing.png',
            'landing_plywood.png'
        ]
        for img in images:
            resp = self.client.get(f'/static/images/{img}')
            self.assertEqual(resp.status_code, 200, f"Image {img} returned status {resp.status_code}")

    def test_03_logged_in_customer_navigation(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 7
            sess["role"] = "customer"
            sess["user_name"] = "Monica"
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('Customer Portal', html)

    def test_04_admin_and_driver_redirect(self):
        # Admin redirect
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["role"] = "admin"
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/admin/dashboard', resp.headers['Location'])

        # Driver redirect
        with self.client.session_transaction() as sess:
            sess["user_id"] = 5
            sess["role"] = "driver"
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/driver/dashboard', resp.headers['Location'])

if __name__ == '__main__':
    unittest.main()

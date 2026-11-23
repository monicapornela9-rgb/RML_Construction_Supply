import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'RML')))
from app import app
from db import get_db

class AuthPagesTest(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_01_login_page_renders_figma_layout(self):
        resp = self.client.get('/login')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        
        # Check Figma Structure Classes
        self.assertIn('figma-auth-screen-layout', html)
        self.assertIn('figma-auth-header', html)
        self.assertIn('figma-auth-main', html)
        self.assertIn('figma-auth-hero-pane', html)
        self.assertIn('figma-auth-form-pane', html)
        self.assertIn('figma-auth-form-card', html)
        self.assertIn('figma-auth-footer', html)
        
        # Check Brand and Content
        self.assertIn('RML Construction Supply', html)
        self.assertIn('Customer Portal', html)
        self.assertIn('Work Email', html)
        self.assertIn('Keep me signed in on this device', html)
        self.assertIn('Sign In', html)
        self.assertIn('Other sign-in options', html)
        self.assertIn('google_icon.svg', html)
        self.assertIn('microsoft_icon.svg', html)
        self.assertIn('Register Now &rarr;', html)
        
        # Ensure standard top navbar is NOT rendered (avoid double navbar)
        self.assertNotIn('Customer Login</a>', html)
        self.assertNotIn('rml-sidebar', html)

    def test_02_register_page_renders_figma_layout(self):
        resp = self.client.get('/register')
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        
        # Check Figma Structure Classes
        self.assertIn('figma-auth-screen-layout', html)
        self.assertIn('figma-auth-header', html)
        self.assertIn('figma-auth-main', html)
        self.assertIn('figma-auth-hero-pane', html)
        self.assertIn('figma-auth-form-card', html)
        self.assertIn('figma-auth-footer', html)
        
        # Check All 6 Required Fields
        self.assertIn('name="name"', html)
        self.assertIn('name="email"', html)
        self.assertIn('name="phone"', html)
        self.assertIn('name="address"', html)
        self.assertIn('name="password"', html)
        self.assertIn('name="confirm_password"', html)
        self.assertIn('Create Account', html)
        self.assertIn('Sign in &rarr;', html)

    def test_03_static_assets_exist(self):
        resp_hero = self.client.get('/static/images/figma_auth_hero.png')
        self.assertEqual(resp_hero.status_code, 200)
        
        resp_google = self.client.get('/static/images/google_icon.svg')
        self.assertEqual(resp_google.status_code, 200)
        
        resp_ms = self.client.get('/static/images/microsoft_icon.svg')
        self.assertEqual(resp_ms.status_code, 200)

    def test_04_login_failed_shows_alert(self):
        resp = self.client.post('/login', data={
            'identifier': 'nonexistent@example.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('alert', html)
        self.assertIn('Customer Portal', html)

if __name__ == '__main__':
    unittest.main()

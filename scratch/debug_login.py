import os, sys
PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "RML")
sys.path.insert(0, PROJECT_DIR)
from app import app

client = app.test_client()
res = client.post("/login", data={"email": "customer@rml.com", "password": "customer123"}, follow_redirects=True)
print("Status:", res.status_code)
print("History:", [r.location for r in res.history])
print("First 300 chars of response:", res.get_data(as_text=True)[:300])

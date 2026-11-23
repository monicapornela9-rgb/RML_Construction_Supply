import os
import sys

sys.path.insert(0, os.path.abspath('RML'))
from app import app
import inspect
from routes import main_bp

print("=== ALL REGISTERED ROUTES IN FLASK APP ===")
customer_routes = []
for rule in app.url_map.iter_rules():
    func = app.view_functions[rule.endpoint]
    # check source file
    source_file = inspect.getsourcefile(func)
    if 'routes.py' in str(source_file):
        route_info = {
            'endpoint': rule.endpoint,
            'rule': rule.rule,
            'methods': [m for m in rule.methods if m not in ('HEAD', 'OPTIONS')]
        }
        # Let's inspect source code to see if it's customer-accessible or admin-only
        try:
            src = inspect.getsource(func)
            if 'admin_required' in src or 'driver_required' in src or 'role in ("admin"' in src:
                route_info['access'] = 'admin/driver'
            elif 'customer_required' in src or 'login_required' in src:
                route_info['access'] = 'customer_authenticated'
            else:
                route_info['access'] = 'public'
            
            # Find template rendered
            import re
            tmpls = re.findall(r'render_template\s*\(\s*["\']([^"\']+)["\']', src)
            route_info['templates'] = tmpls
        except Exception as e:
            route_info['access'] = 'unknown'
            route_info['templates'] = []
            
        customer_routes.append(route_info)

for r in sorted(customer_routes, key=lambda x: x['rule']):
    if r['access'] in ('customer_authenticated', 'public'):
        print(f"[{r['access']}] {r['rule']} ({', '.join(r['methods'])}) -> {r['endpoint']} -> {r['templates']}")

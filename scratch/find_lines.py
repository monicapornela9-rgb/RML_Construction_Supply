with open(r'c:\xampp\htdocs\RML_Construction_Supply\RML\routes.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'action == "verify_payment"' in l or "action == 'verify_payment'" in l:
        print(f'verify_payment at {i+1}')
    if 'action == "authorize_delivery"' in l or "admin_order_authorize_delivery" in l:
        print(f'authorize_delivery at {i+1}')
    if 'action == "confirm_delivered"' in l:
        print(f'confirm_delivered at {i+1}')
    if "new_status == 'en_route'" in l or 'new_status == "en_route"' in l:
        print(f'en_route at {i+1}')

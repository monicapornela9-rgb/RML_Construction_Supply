import os

customer_templates = [
    'customer/dashboard.html',
    'customer/catalog.html',
    'customer/cart.html',
    'customer/checkout.html',
    'customer/payment.html',
    'customer/payment_history.html',
    'customer/orders.html',
    'customer/tracking.html',
    'customer/delivery_tracking.html',
    'customer/profile.html',
    'customer/notifications.html',
    'customer/support.html',
    'customer/order_confirmation.html'
]

base_dir = r'C:\xampp\htdocs\RML_Construction_Supply\RML\templates'

for rel in customer_templates:
    full = os.path.join(base_dir, rel)
    if os.path.exists(full):
        with open(full, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f"{rel}: {len(lines)} lines")
    else:
        print(f"{rel}: NOT FOUND")

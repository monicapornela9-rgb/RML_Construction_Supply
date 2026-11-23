import os

for root, dirs, files in os.walk(r'c:\xampp\htdocs\RML_Construction_Supply\RML'):
    for file in files:
        if file.endswith('.py'):
            p = os.path.join(root, file)
            with open(p, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'context_processor' in content:
                    print(f'{file} has context_processor')
                if 'cart_count' in content:
                    print(f'{file} has cart_count')

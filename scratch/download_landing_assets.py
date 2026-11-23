import urllib.request
import os

assets = {
    'landing_page_screenshot.png': 'https://www.figma.com/api/mcp/asset/d9605e94-e641-44e6-a442-480337b99f93.png',
    'landing_steel_bars.png': 'https://www.figma.com/api/mcp/asset/56a65118-47bc-4e89-942b-832085dca55f/6a4de.png',
    'landing_cement.png': 'https://www.figma.com/api/mcp/asset/56a65118-47bc-4e89-942b-832085dca55f/c9bb7.png',
    'landing_roofing.png': 'https://www.figma.com/api/mcp/asset/56a65118-47bc-4e89-942b-832085dca55f/983a4.png',
    'landing_plywood.png': 'https://www.figma.com/api/mcp/asset/56a65118-47bc-4e89-942b-832085dca55f/5ec23.png'
}

dest_dir = r'C:\xampp\htdocs\RML_Construction_Supply\RML\static\images'
os.makedirs(dest_dir, exist_ok=True)

headers = {'User-Agent': 'Mozilla/5.0'}

for name, url in assets.items():
    dest_path = os.path.join(dest_dir, name)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp, open(dest_path, 'wb') as f:
            f.write(resp.read())
        print(f"Downloaded {name}: {os.path.getsize(dest_path)} bytes")
    except Exception as e:
        print(f"Error downloading {name}: {e}")

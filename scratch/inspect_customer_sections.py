import re

path = r'C:\Users\kirve\.gemini\antigravity\brain\4fd091b7-dd38-4d7a-97f4-23633ce633cd\.system_generated\steps\3179\output.txt'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect sections:
sections_to_check = [
    ('172:36', '01 · Account and catalog'),
    ('172:2225', '02 · Steel'),
    ('172:3720', '03 · Plywood'),
    ('172:5721', '04 · Cart → checkout'),
    ('172:7337', '05 · Payments'),
    ('172:9364', '06 · Track and support')
]

for sec_id, sec_title in sections_to_check:
    print(f"\n==================== Section {sec_id}: {sec_title} ====================")
    # find section start
    m = re.search(rf'<section id="{sec_id}" name="([^"]+)"', text)
    if m:
        start_pos = m.start()
        # Find all frames inside this section (until next section)
        next_sec = re.search(r'<section ', text[start_pos+100:])
        end_pos = start_pos + 100 + next_sec.start() if next_sec else start_pos + 50000
        sec_text = text[start_pos:end_pos]
        
        frames = re.findall(r'<frame id="([^"]+)" name="([^"]+)"[^>]*width="([^"]+)"[^>]*height="([^"]+)"', sec_text)
        # filter for top-level or main screens (width >= 1000)
        screens = [(fid, fn, w, h) for fid, fn, w, h in frames if float(w) >= 1200]
        print(f"Total main screens: {len(screens)}")
        for fid, fn, w, h in screens:
            print(f"  [{fid}] {fn} ({w}x{h})")

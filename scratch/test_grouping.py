import sqlite3
from datetime import datetime, date, timedelta

conn = sqlite3.connect('RML/rml_database.db')
conn.row_factory = sqlite3.Row
notifs = conn.execute('SELECT n.*, o.order_code FROM notifications n LEFT JOIN orders o ON o.id = n.order_id WHERE n.user_id = 38 ORDER BY n.created_at DESC, n.id DESC').fetchall()

now = datetime.now()

def format_relative_time(dt_str, now=None):
    if not dt_str:
        return ''
    if now is None:
        now = datetime.now()
    try:
        if len(dt_str) == 10:
            dt = datetime.strptime(dt_str, '%Y-%m-%d')
        elif len(dt_str) >= 19:
            dt = datetime.strptime(dt_str[:19], '%Y-%m-%d %H:%M:%S')
        else:
            dt = datetime.fromisoformat(dt_str)
    except Exception:
        return dt_str

    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 0:
        return 'Just now'
    elif seconds < 60:
        return f'{seconds}s ago' if seconds > 5 else 'Just now'
    elif seconds < 3600:
        mins = seconds // 60
        return f'{mins}m ago'
    elif seconds < 86400 and dt.date() == now.date():
        hours = seconds // 3600
        return f'{hours}h ago'
    elif dt.date() == (now.date() - timedelta(days=1)):
        return f"Yesterday, {dt.strftime('%I:%M %p')}"
    elif dt.year == now.year:
        return dt.strftime('%b %d, %I:%M %p')
    else:
        return dt.strftime('%b %d, %Y, %I:%M %p')

def get_date_group(dt_str, now=None):
    if not dt_str:
        return 'Earlier'
    if now is None:
        now = datetime.now()
    try:
        dt = datetime.strptime(dt_str[:10], '%Y-%m-%d').date()
        if dt == now.date():
            return 'Today'
        elif dt == (now.date() - timedelta(days=1)):
            return 'Yesterday'
        else:
            return 'Earlier'
    except Exception:
        return 'Earlier'

grouped = {'Today': [], 'Yesterday': [], 'Earlier': []}
for r in notifs:
    item = dict(r)
    item['relative_time'] = format_relative_time(item.get('created_at'), now)
    grp = get_date_group(item.get('created_at'), now)
    item['date_group'] = grp
    grouped[grp].append(item)

print({k: len(v) for k, v in grouped.items()})
for k, v in grouped.items():
    if v:
        print(f"=== {k} ({len(v)}) ===")
        for it in v[:3]:
            print(f"  {it['title']} | {it['relative_time']} | Order {it['order_code']}")
conn.close()

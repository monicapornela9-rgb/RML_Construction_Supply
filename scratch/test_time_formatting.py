from datetime import datetime, date, timedelta

def format_relative_time(dt_str, now=None):
    if not dt_str:
        return ""
    if now is None:
        now = datetime.now()
    try:
        if len(dt_str) == 10:
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
        elif len(dt_str) >= 19:
            dt = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.fromisoformat(dt_str)
    except Exception:
        return dt_str

    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 0:
        return "Just now"
    elif seconds < 60:
        return f"{seconds}s ago" if seconds > 5 else "Just now"
    elif seconds < 3600:
        mins = seconds // 60
        return f"{mins} minute{'s' if mins > 1 else ''} ago"
    elif seconds < 86400 and dt.date() == now.date():
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif dt.date() == (now.date() - timedelta(days=1)):
        return f"Yesterday at {dt.strftime('%I:%M %p')}"
    elif dt.year == now.year:
        return dt.strftime("%b %d at %I:%M %p")
    else:
        return dt.strftime("%b %d, %Y at %I:%M %p")

def get_date_group(dt_str, now=None):
    if not dt_str:
        return "Earlier"
    if now is None:
        now = datetime.now()
    try:
        dt = datetime.strptime(dt_str[:10], "%Y-%m-%d").date()
        if dt == now.date():
            return "Today"
        elif dt == (now.date() - timedelta(days=1)):
            return "Yesterday"
        else:
            return "Earlier"
    except Exception:
        return "Earlier"

test_dates = [
    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    (datetime.now() - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
    (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
    (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
    "2026-11-21 04:25:08",
    "2026-11-20 00:05:57",
]

for d in test_dates:
    print(f"Date: {d} -> Group: {get_date_group(d)} -> Relative: {format_relative_time(d)}")

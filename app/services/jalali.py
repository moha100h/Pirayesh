import jdatetime
from datetime import datetime, date, timedelta

_WEEKDAYS = ["دوشنبه","سه‌شنبه","چهارشنبه","پنج‌شنبه","جمعه","شنبه","یکشنبه"]

def to_jalali(dt) -> str:
    """datetime یا date → رشته شمسی"""
    try:
        if isinstance(dt, datetime):
            jd = jdatetime.datetime.fromgregorian(datetime=dt)
        else:
            jd = jdatetime.date.fromgregorian(date=dt)
        return f"{jd.year}/{jd.month:02d}/{jd.day:02d}"
    except Exception:
        return str(dt)

def to_jalali_full(dt) -> str:
    """با نام روز هفته: شنبه ۱۴۰۵/۰۳/۰۸"""
    try:
        if isinstance(dt, str):
            dt = date.fromisoformat(dt)
        if isinstance(dt, datetime):
            d = dt.date()
        else:
            d = dt
        jd = jdatetime.date.fromgregorian(date=d)
        wd = _WEEKDAYS[d.weekday()]
        return f"{wd} {jd.year}/{jd.month:02d}/{jd.day:02d}"
    except Exception:
        return str(dt)

def next_7_days() -> list:
    """لیست ۷ روز آینده به فرمت YYYY-MM-DD"""
    today = date.today()
    return [(today + timedelta(days=i)).isoformat() for i in range(1, 8)]

def fmt_price(n) -> str:
    try: return f"{int(n):,} تومان"
    except: return str(n)

from datetime import datetime

_MONTHS = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
           "مهر","آبان","آذر","دی","بهمن","اسفند"]

def to_jalali(dt: datetime) -> str:
    if dt is None: return "—"
    try:
        import jdatetime
        jd = jdatetime.datetime.fromgregorian(datetime=dt)
        return f"{jd.year}/{jd.month:02d}/{jd.day:02d}"
    except Exception:
        return dt.strftime("%Y-%m-%d")

def fmt(n) -> str:
    try: return f"{int(n):,} ت"
    except: return str(n)

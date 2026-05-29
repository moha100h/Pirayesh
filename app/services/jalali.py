import jdatetime
from datetime import date, timedelta

WEEKDAYS_FA = {0:"دوشنبه",1:"سه‌شنبه",2:"چهارشنبه",3:"پنج‌شنبه",4:"جمعه",5:"شنبه",6:"یکشنبه"}

def to_jalali(d) -> str:
    """YYYY-MM-DD string → شمسی مختصر مثل ۱۴۰۵/۰۳/۰۸"""
    if isinstance(d, str): d = date.fromisoformat(d)
    jd = jdatetime.date.fromgregorian(date=d)
    return f"{jd.year}/{jd.month:02d}/{jd.day:02d}"

def to_jalali_full(d) -> str:
    """YYYY-MM-DD string → شنبه ۸ خرداد"""
    if isinstance(d, str): d = date.fromisoformat(d)
    jd = jdatetime.date.fromgregorian(date=d)
    months = ["","فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
              "مهر","آبان","آذر","دی","بهمن","اسفند"]
    wd = WEEKDAYS_FA.get(d.weekday(), "")
    return f"{wd} {jd.day} {months[jd.month]}"

def next_3_days() -> list:
    """۳ روز آینده (نه امروز) به فرمت YYYY-MM-DD"""
    today = date.today()
    return [(today + timedelta(days=i)).isoformat() for i in range(1, 4)]

def fmt_price(p) -> str:
    try: return f"{int(p):,} تومان"
    except: return str(p)

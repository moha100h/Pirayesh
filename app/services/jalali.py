import jdatetime
from datetime import date, timedelta
import pytz
from datetime import datetime

TEHRAN_TZ = pytz.timezone("Asia/Tehran")

WEEKDAYS_FA = {
    0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه",
    3: "پنج‌شنبه", 4: "جمعه", 5: "شنبه", 6: "یکشنبه"
}
MONTHS_FA = ["","فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
             "مهر","آبان","آذر","دی","بهمن","اسفند"]

def today_tehran() -> date:
    """تاریخ امروز بر اساس timezone تهران"""
    return datetime.now(TEHRAN_TZ).date()

def to_gregorian(jalali_str: str):
    """
    تبدیل تاریخ شمسی به میلادی
    ورودی: 1405/03/09 یا 1405-03-09
    خروجی: date object یا None در صورت خطا
    """
    try:
        jalali_str = jalali_str.strip().replace("-", "/")
        parts = jalali_str.split("/")
        if len(parts) != 3:
            return None
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        jd = jdatetime.date(y, m, d)
        return jd.togregorian()
    except:
        return None

def to_jalali(d) -> str:
    """میلادی → شمسی مختصر: ۱۴۰۵/۰۳/۰۸"""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    jd = jdatetime.date.fromgregorian(date=d)
    return f"{jd.year}/{jd.month:02d}/{jd.day:02d}"

def to_jalali_full(d) -> str:
    """میلادی → شمسی کامل: شنبه ۸ خرداد"""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    jd = jdatetime.date.fromgregorian(date=d)
    wd = WEEKDAYS_FA.get(d.weekday(), "")
    return f"{wd} {jd.day} {MONTHS_FA[jd.month]}"

def to_jalali_with_year(d) -> str:
    """میلادی → شمسی با سال: شنبه ۸ خرداد ۱۴۰۵"""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    jd = jdatetime.date.fromgregorian(date=d)
    wd = WEEKDAYS_FA.get(d.weekday(), "")
    return f"{wd} {jd.day} {MONTHS_FA[jd.month]} {jd.year}"

def next_3_days() -> list:
    """۳ روز آینده (نه امروز) — timezone تهران"""
    today = today_tehran()
    return [(today + timedelta(days=i)).isoformat() for i in range(1, 4)]

def next_n_days(n: int = 14) -> list:
    """n روز آینده برای پنل ادمین — timezone تهران"""
    today = today_tehran()
    return [(today + timedelta(days=i)).isoformat() for i in range(1, n + 1)]

def fmt_price(p) -> str:
    try:
        return f"{int(p):,} تومان"
    except:
        return str(p)

def validate_time(t: str) -> bool:
    """اعتبارسنجی فرمت HH:MM"""
    try:
        parts = t.strip().split(":")
        if len(parts) != 2:
            return False
        h, m = int(parts[0]), int(parts[1])
        return 0 <= h <= 23 and 0 <= m <= 59
    except:
        return False

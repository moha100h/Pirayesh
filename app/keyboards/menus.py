from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_menu(is_admin: bool = False, booking: bool = True,
              services: bool = True, payment: bool = True) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    if booking:
        kb.row(KeyboardButton(text="📅 نوبت‌گیری"))
    if services:
        kb.row(KeyboardButton(text="✂️ خدمات و قیمت‌ها"))
    kb.row(KeyboardButton(text="📋 نوبت‌های من"))
    kb.row(KeyboardButton(text="📞 اطلاعات آرایشگاه"))
    if is_admin:
        kb.row(KeyboardButton(text="⚙️ پنل مدیریت"))
    return kb.as_markup(resize_keyboard=True)


def services_kb(services: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in services:
        kb.row(InlineKeyboardButton(
            text=f"✂️ {s.name}  |  {s.price:,} ت  ({s.duration} دقیقه)",
            callback_data=f"book:svc:{s.id}"
        ))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="nav:main"))
    return kb.as_markup()


def slots_kb(slots: list, service_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for sl in slots:
        kb.button(text=f"🕐 {sl.time}", callback_data=f"book:slot:{sl.id}:{service_id}")
    kb.adjust(3)
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="book:back:svc"))
    return kb.as_markup()


def dates_kb(dates: list, service_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for d in dates:
        kb.row(InlineKeyboardButton(text=f"📅 {d}", callback_data=f"book:date:{d}:{service_id}"))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="book:back:svc"))
    return kb.as_markup()


def confirm_booking_kb(slot_id: int, service_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ تایید نوبت", callback_data=f"book:confirm:{slot_id}:{service_id}"),
        InlineKeyboardButton(text="❌ انصراف",     callback_data="nav:main")
    )
    return kb.as_markup()


def payment_kb(booking_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📸 ارسال رسید پرداخت", callback_data=f"pay:send:{booking_id}"))
    kb.row(InlineKeyboardButton(text="💵 پرداخت حضوری",      callback_data=f"pay:cash:{booking_id}"))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت",             callback_data="nav:main"))
    return kb.as_markup()


def my_bookings_kb(bookings: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    S = {"pending":"⏳","confirmed":"✅","cancelled":"❌","done":"💈"}
    for b in bookings:
        sv = b.status.value if hasattr(b.status,"value") else b.status
        label = f"{S.get(sv,'📋')} {b.slot.date} {b.slot.time} — {b.service.name}"
        kb.row(InlineKeyboardButton(text=label, callback_data=f"mybk:view:{b.id}"))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="nav:main"))
    return kb.as_markup()


def booking_detail_kb(booking_id: int, status: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if status in ("pending","confirmed"):
        kb.row(InlineKeyboardButton(text="❌ لغو نوبت", callback_data=f"mybk:cancel:{booking_id}"))
    kb.row(InlineKeyboardButton(text="🔙 نوبت‌های من", callback_data="mybk:list"))
    return kb.as_markup()


def admin_main_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📋 نوبت‌های امروز", callback_data="adm:bookings:today"),
        InlineKeyboardButton(text="📅 همه نوبت‌ها",    callback_data="adm:bookings:all")
    )
    kb.row(
        InlineKeyboardButton(text="✂️ مدیریت خدمات",  callback_data="adm:services"),
        InlineKeyboardButton(text="🕐 مدیریت زمان‌ها", callback_data="adm:slots")
    )
    kb.row(
        InlineKeyboardButton(text="💳 پرداخت‌های معلق", callback_data="adm:payments"),
        InlineKeyboardButton(text="📊 آمار",             callback_data="adm:stats")
    )
    kb.row(
        InlineKeyboardButton(text="🏪 اطلاعات آرایشگاه", callback_data="adm:shopinfo"),
        InlineKeyboardButton(text="🔧 تنظیمات",           callback_data="adm:settings")
    )
    kb.row(InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main"))
    return kb.as_markup()


def admin_booking_kb(booking_id: int, status: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if status == "pending":
        kb.row(
            InlineKeyboardButton(text="✅ تایید",  callback_data=f"adm:bk:confirm:{booking_id}"),
            InlineKeyboardButton(text="❌ رد",     callback_data=f"adm:bk:cancel:{booking_id}")
        )
    if status == "confirmed":
        kb.row(
            InlineKeyboardButton(text="💈 انجام شد", callback_data=f"adm:bk:done:{booking_id}"),
            InlineKeyboardButton(text="❌ لغو",       callback_data=f"adm:bk:cancel:{booking_id}")
        )
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="adm:bookings:today"))
    return kb.as_markup()


def admin_payment_kb(payment_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ تایید پرداخت", callback_data=f"adm:pay:confirm:{payment_id}"),
        InlineKeyboardButton(text="❌ رد پرداخت",    callback_data=f"adm:pay:reject:{payment_id}")
    )
    return kb.as_markup()


def admin_settings_kb(booking: bool, payment: bool, services: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(
        text=f"{'🟢' if booking  else '🔴'} نوبت‌گیری",
        callback_data="adm:toggle:booking"
    ))
    kb.row(InlineKeyboardButton(
        text=f"{'🟢' if payment  else '🔴'} پرداخت آنلاین",
        callback_data="adm:toggle:payment"
    ))
    kb.row(InlineKeyboardButton(
        text=f"{'🟢' if services else '🔴'} نمایش خدمات",
        callback_data="adm:toggle:services"
    ))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="adm:main"))
    return kb.as_markup()


def admin_shop_info_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✏️ نام آرایشگاه", callback_data="adm:shop:set:name"),
        InlineKeyboardButton(text="📞 تلفن",          callback_data="adm:shop:set:phone")
    )
    kb.row(
        InlineKeyboardButton(text="📍 آدرس",          callback_data="adm:shop:set:address"),
        InlineKeyboardButton(text="💳 شماره کارت",    callback_data="adm:shop:set:card")
    )
    kb.row(InlineKeyboardButton(text="👤 نام صاحب کارت", callback_data="adm:shop:set:holder"))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت",        callback_data="adm:main"))
    return kb.as_markup()


def back_btn(to: str = "nav:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 بازگشت", callback_data=to)
    ]])

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.db.models import (Booking, BookingStatus, Service, TimeSlot,
                            Payment, PaymentStatus, HolidayDate)
from app.keyboards.menus import (
    admin_main_kb, admin_booking_kb,
    admin_payment_notify_kb, admin_settings_kb,
    admin_shop_info_kb, admin_holidays_kb, back_btn
)
from app.services.jalali import (
    to_jalali_full, to_jalali_with_year, to_jalali,
    fmt_price, next_n_days, today_tehran, validate_time, to_gregorian
)
from app.config import config
import os

router = Router()

class IsAdmin(Filter):
    async def __call__(self, event) -> bool:
        return getattr(event.from_user, "id", None) in config.ADMIN_IDS

class ServiceFSM(StatesGroup):
    name = State(); price = State(); duration = State()

class SlotFSM(StatesGroup):
    pick_date = State()   # انتخاب تاریخ از دکمه یا تایپ شمسی
    times     = State()   # وارد کردن ساعت‌ها

class ShopFSM(StatesGroup):
    value = State()

class HolidayFSM(StatesGroup):
    date = State(); label = State()

router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

def _update_env(key, value):
    env_path = ".env"
    try:
        lines = open(env_path).readlines() if os.path.exists(env_path) else []
        found, new_lines = False, []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n"); found = True
            else:
                new_lines.append(line)
        if not found: new_lines.append(f"{key}={value}\n")
        open(env_path, "w").writelines(new_lines)
    except: pass

# ── پنل اصلی ─────────────────────────────────────────────────────────────────
@router.message(F.text == "⚙️ پنل مدیریت")
async def admin_panel(msg: Message):
    await msg.answer("⚙️ <b>پنل مدیریت</b>", reply_markup=admin_main_kb(), parse_mode="HTML")

@router.callback_query(F.data == "adm:main")
async def adm_main(cb: CallbackQuery):
    await cb.message.edit_text("⚙️ <b>پنل مدیریت</b>", reply_markup=admin_main_kb(), parse_mode="HTML")
    await cb.answer()

# ── نوبت‌های امروز ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:bookings:today")
async def adm_bookings_today(cb: CallbackQuery, session: AsyncSession):
    today = today_tehran().isoformat()
    r = await session.execute(
        select(Booking).join(Booking.slot).where(TimeSlot.date == today)
        .options(selectinload(Booking.user), selectinload(Booking.service), selectinload(Booking.slot))
        .order_by(TimeSlot.time)
    )
    bookings = r.scalars().all()
    if not bookings:
        await cb.message.edit_text(
            f"📋 امروز <b>{to_jalali_with_year(today)}</b> نوبتی ندارید.",
            reply_markup=back_btn("adm:main"), parse_mode="HTML"
        )
        await cb.answer(); return

    S = {"pending":"⏳","confirmed":"✅","cancelled":"❌","done":"💈"}
    kb = InlineKeyboardBuilder()
    for b in bookings:
        sv = b.status.value if hasattr(b.status,"value") else b.status
        name = b.user.full_name if b.user else "—"
        kb.row(InlineKeyboardButton(
            text=f"{S.get(sv,'📋')} {b.slot.time} — {name} — {b.service.name}",
            callback_data=f"adm:bk:view:{b.id}"
        ))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="adm:main"))
    await cb.message.edit_text(
        f"📋 <b>نوبت‌های امروز — {to_jalali_with_year(today)}</b>",
        reply_markup=kb.as_markup(), parse_mode="HTML"
    )
    await cb.answer()

@router.callback_query(F.data == "adm:bookings:all")
async def adm_bookings_all(cb: CallbackQuery, session: AsyncSession):
    r = await session.execute(
        select(Booking)
        .options(selectinload(Booking.user), selectinload(Booking.service), selectinload(Booking.slot))
        .order_by(Booking.id.desc()).limit(20)
    )
    bookings = r.scalars().all()
    if not bookings:
        await cb.message.edit_text("📋 هیچ نوبتی ثبت نشده.", reply_markup=back_btn("adm:main"))
        await cb.answer(); return
    S = {"pending":"⏳","confirmed":"✅","cancelled":"❌","done":"💈"}
    kb = InlineKeyboardBuilder()
    for b in bookings:
        sv = b.status.value if hasattr(b.status,"value") else b.status
        name = b.user.full_name if b.user else "—"
        date_str = to_jalali_full(b.slot.date) if b.slot else "—"
        time_str = b.slot.time if b.slot else "—"
        kb.row(InlineKeyboardButton(
            text=f"{S.get(sv,'📋')} {date_str} {time_str} — {name}",
            callback_data=f"adm:bk:view:{b.id}"
        ))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="adm:main"))
    await cb.message.edit_text("📋 <b>آخرین ۲۰ نوبت</b>", reply_markup=kb.as_markup(), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("adm:bk:view:"))
async def adm_bk_view(cb: CallbackQuery, session: AsyncSession):
    bk_id = int(cb.data.split(":")[3])
    r = await session.execute(
        select(Booking).where(Booking.id == bk_id)
        .options(selectinload(Booking.user), selectinload(Booking.service), selectinload(Booking.slot))
    )
    bk = r.scalar_one_or_none()
    if not bk: await cb.answer("یافت نشد!", show_alert=True); return
    sv = bk.status.value if hasattr(bk.status,"value") else bk.status
    S = {"pending":"⏳ در انتظار","confirmed":"✅ تایید","cancelled":"❌ لغو","done":"💈 انجام شد"}
    u = bk.user
    text = (
        f"📋 <b>نوبت #{bk.id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 {u.full_name if u else '—'}\n"
        f"📞 {u.phone if u else '—'}\n"
        f"📱 @{u.username if u and u.username else '—'}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✂️ {bk.service.name}  |  {fmt_price(bk.service.price)}\n"
        f"📅 {to_jalali_with_year(bk.slot.date)}\n"
        f"🕐 ساعت: {bk.slot.time}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"وضعیت: {S.get(sv,sv)}"
    )
    await cb.message.edit_text(text, reply_markup=admin_booking_kb(bk.id, sv), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("adm:bk:confirm:"))
async def adm_bk_confirm(cb: CallbackQuery, session: AsyncSession):
    bk_id = int(cb.data.split(":")[3])
    bk = await session.get(Booking, bk_id)
    if not bk: await cb.answer("یافت نشد!", show_alert=True); return
    bk.status = BookingStatus.CONFIRMED
    await session.commit()
    try:
        await cb.bot.send_message(bk.user_id,
            "✅ <b>نوبت شما تایید شد!</b>\nمنتظرتان هستیم 💈", parse_mode="HTML")
    except: pass
    await cb.message.edit_text(f"✅ نوبت #{bk_id} تایید شد.")
    await cb.answer()

@router.callback_query(F.data.startswith("adm:bk:cancel:"))
async def adm_bk_cancel(cb: CallbackQuery, session: AsyncSession):
    bk_id = int(cb.data.split(":")[3])
    r = await session.execute(
        select(Booking).where(Booking.id == bk_id).options(selectinload(Booking.slot))
    )
    bk = r.scalar_one_or_none()
    if not bk: await cb.answer("یافت نشد!", show_alert=True); return
    bk.status = BookingStatus.CANCELLED
    bk.slot.is_booked = False
    await session.commit()
    try:
        await cb.bot.send_message(bk.user_id,
            "❌ <b>نوبت شما لغو شد.</b>\nبرای نوبت جدید /start را بزنید.", parse_mode="HTML")
    except: pass
    await cb.message.edit_text(f"❌ نوبت #{bk_id} لغو شد.")
    await cb.answer()

@router.callback_query(F.data.startswith("adm:bk:done:"))
async def adm_bk_done(cb: CallbackQuery, session: AsyncSession):
    bk_id = int(cb.data.split(":")[3])
    bk = await session.get(Booking, bk_id)
    if not bk: await cb.answer("یافت نشد!", show_alert=True); return
    bk.status = BookingStatus.DONE
    await session.commit()
    await cb.message.edit_text(f"💈 نوبت #{bk_id} انجام شد.")
    await cb.answer()

# ── پرداخت‌ها ─────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:payments")
async def adm_payments(cb: CallbackQuery, session: AsyncSession):
    r = await session.execute(
        select(Payment).where(Payment.status == PaymentStatus.SUBMITTED)
        .options(selectinload(Payment.booking).selectinload(Booking.user))
    )
    payments = r.scalars().all()
    if not payments:
        await cb.message.edit_text("✅ پرداخت معلقی وجود ندارد.", reply_markup=back_btn("adm:main"))
        await cb.answer(); return
    kb = InlineKeyboardBuilder()
    for p in payments:
        name = p.booking.user.full_name if p.booking and p.booking.user else "—"
        kb.row(InlineKeyboardButton(text=f"💳 #{p.id} — {name}", callback_data=f"adm:pay:view:{p.id}"))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="adm:main"))
    await cb.message.edit_text("💳 <b>پرداخت‌های معلق:</b>", reply_markup=kb.as_markup(), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("adm:pay:view:"))
async def adm_pay_view(cb: CallbackQuery, session: AsyncSession):
    pay_id = int(cb.data.split(":")[3])
    r = await session.execute(
        select(Payment).where(Payment.id == pay_id)
        .options(selectinload(Payment.booking).selectinload(Booking.user),
                 selectinload(Payment.booking).selectinload(Booking.service),
                 selectinload(Payment.booking).selectinload(Booking.slot))
    )
    pay = r.scalar_one_or_none()
    if not pay: await cb.answer("یافت نشد!", show_alert=True); return
    bk = pay.booking
    u = bk.user if bk else None
    text = (
        f"💳 <b>پرداخت #{pay.id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 {u.full_name if u else '—'}\n"
        f"📞 {u.phone if u else '—'}\n"
        f"📱 @{u.username if u and u.username else '—'}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✂️ {bk.service.name if bk else '—'}\n"
        f"📅 {to_jalali_with_year(bk.slot.date) if bk else '—'}  🕐 {bk.slot.time if bk else '—'}\n"
        f"💰 {fmt_price(bk.service.price) if bk else '—'}"
    )
    await cb.message.edit_text(text, reply_markup=admin_payment_notify_kb(pay.id), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("adm:pay:receipt:"))
async def adm_pay_receipt(cb: CallbackQuery, session: AsyncSession):
    pay_id = int(cb.data.split(":")[3])
    r = await session.execute(select(Payment).where(Payment.id == pay_id))
    pay = r.scalar_one_or_none()
    if not pay or not pay.receipt_file:
        await cb.answer("رسیدی یافت نشد!", show_alert=True); return
    from app.keyboards.menus import admin_payment_kb
    await cb.message.answer_photo(
        photo=pay.receipt_file,
        caption=f"🧾 رسید پرداخت #{pay_id}",
        reply_markup=admin_payment_kb(pay_id)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("adm:pay:confirm:"))
async def adm_pay_confirm(cb: CallbackQuery, session: AsyncSession):
    pay_id = int(cb.data.split(":")[3])
    r = await session.execute(
        select(Payment).where(Payment.id == pay_id).options(selectinload(Payment.booking))
    )
    pay = r.scalar_one_or_none()
    if not pay: await cb.answer("یافت نشد!", show_alert=True); return
    pay.status = PaymentStatus.CONFIRMED
    pay.booking.status = BookingStatus.CONFIRMED
    await session.commit()
    try:
        await cb.bot.send_message(pay.booking.user_id,
            "✅ <b>پرداخت شما تایید شد!</b>\nنوبتتان قطعی است. منتظرتان هستیم 💈", parse_mode="HTML")
    except: pass
    await cb.message.edit_text("✅ پرداخت تایید شد.")
    await cb.answer()

@router.callback_query(F.data.startswith("adm:pay:reject:"))
async def adm_pay_reject(cb: CallbackQuery, session: AsyncSession):
    pay_id = int(cb.data.split(":")[3])
    r = await session.execute(
        select(Payment).where(Payment.id == pay_id).options(selectinload(Payment.booking))
    )
    pay = r.scalar_one_or_none()
    if not pay: await cb.answer("یافت نشد!", show_alert=True); return
    pay.status = PaymentStatus.REJECTED
    await session.commit()
    try:
        await cb.bot.send_message(pay.booking.user_id,
            "❌ <b>رسید پرداخت رد شد.</b>\nلطفاً مجدداً ارسال کنید یا با آرایشگاه تماس بگیرید.", parse_mode="HTML")
    except: pass
    await cb.message.edit_text("❌ پرداخت رد شد.")
    await cb.answer()

# ── خدمات ─────────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:services")
async def adm_services(cb: CallbackQuery, session: AsyncSession):
    r = await session.execute(select(Service).order_by(Service.id))
    services = r.scalars().all()
    kb = InlineKeyboardBuilder()
    for s in services:
        icon = "🟢" if s.is_active else "🔴"
        kb.row(InlineKeyboardButton(
            text=f"{icon} {s.name} — {s.price:,} ت  ({s.duration} دقیقه)",
            callback_data=f"adm:svc:toggle:{s.id}"
        ))
    kb.row(InlineKeyboardButton(text="➕ خدمت جدید", callback_data="adm:svc:new"))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت",    callback_data="adm:main"))
    await cb.message.edit_text("✂️ <b>مدیریت خدمات</b>\n<i>برای فعال/غیرفعال کردن روی خدمت بزنید</i>",
                                reply_markup=kb.as_markup(), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("adm:svc:toggle:"))
async def adm_svc_toggle(cb: CallbackQuery, session: AsyncSession):
    svc_id = int(cb.data.split(":")[3])
    svc = await session.get(Service, svc_id)
    if not svc: await cb.answer("یافت نشد!", show_alert=True); return
    svc.is_active = not svc.is_active
    await session.commit()
    await adm_services(cb, session)

@router.callback_query(F.data == "adm:svc:new")
async def adm_svc_new(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ServiceFSM.name)
    await cb.message.edit_text("✂️ <b>نام خدمت جدید را وارد کنید:</b>\n<i>مثال: اصلاح موی سر</i>",
                                reply_markup=back_btn("adm:services"), parse_mode="HTML")
    await cb.answer()

@router.message(ServiceFSM.name)
async def svc_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text.strip())
    await state.set_state(ServiceFSM.price)
    await msg.answer("💰 <b>قیمت را وارد کنید (تومان):</b>\n<i>مثال: 150000</i>", parse_mode="HTML")

@router.message(ServiceFSM.price)
async def svc_price(msg: Message, state: FSMContext):
    try:
        price = int(msg.text.strip().replace(",","").replace("،",""))
    except:
        await msg.answer("❌ عدد معتبر وارد کنید:\n<i>مثال: 150000</i>", parse_mode="HTML"); return
    await state.update_data(price=price)
    await state.set_state(ServiceFSM.duration)
    await msg.answer("⏱ <b>مدت زمان را وارد کنید (دقیقه):</b>\n<i>مثال: 30</i>", parse_mode="HTML")

@router.message(ServiceFSM.duration)
async def svc_duration(msg: Message, state: FSMContext, session: AsyncSession):
    try:
        dur = int(msg.text.strip())
    except:
        await msg.answer("❌ عدد معتبر وارد کنید:"); return
    d = await state.get_data()
    svc = Service(name=d["name"], price=d["price"], duration=dur)
    session.add(svc)
    await session.commit()
    await state.clear()
    await msg.answer(
        f"✅ خدمت اضافه شد:\n\n"
        f"✂️ <b>{svc.name}</b>\n"
        f"💰 {fmt_price(svc.price)}\n"
        f"⏱ {svc.duration} دقیقه",
        reply_markup=back_btn("adm:services"), parse_mode="HTML"
    )

# ── مدیریت زمان‌بندی — با دکمه‌های شمسی ─────────────────────────────────────
def _slot_date_picker_kb(page: int = 0) -> tuple:
    """
    ۱۴ روز آینده به صورت دکمه شمسی
    هر صفحه ۷ روز — page=0 هفته اول، page=1 هفته دوم
    """
    days = next_n_days(14)
    start = page * 7
    week = days[start:start+7]
    kb = InlineKeyboardBuilder()
    for d in week:
        label = to_jalali_with_year(d)
        kb.row(InlineKeyboardButton(
            text=f"📅 {label}",
            callback_data=f"adm:slot:date:{d}"
        ))
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ هفته قبل", callback_data=f"adm:slot:page:{page-1}"))
    if page < 1:
        nav_row.append(InlineKeyboardButton(text="هفته بعد ▶️", callback_data=f"adm:slot:page:{page+1}"))
    if nav_row:
        kb.row(*nav_row)
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="adm:main"))
    return kb.as_markup(), week

@router.callback_query(F.data == "adm:slots")
async def adm_slots(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SlotFSM.pick_date)
    kb, _ = _slot_date_picker_kb(0)
    await cb.message.edit_text(
        "📅 <b>مدیریت زمان‌بندی</b>\n\n"
        "روز مورد نظر را انتخاب کنید:",
        reply_markup=kb, parse_mode="HTML"
    )
    await cb.answer()

@router.callback_query(F.data.startswith("adm:slot:page:"))
async def adm_slot_page(cb: CallbackQuery):
    page = int(cb.data.split(":")[3])
    kb, _ = _slot_date_picker_kb(page)
    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("adm:slot:date:"))
async def adm_slot_date_picked(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    date_str = cb.data.split(":")[3]  # YYYY-MM-DD
    await state.update_data(date=date_str)

    # نمایش ساعت‌های موجود برای این روز
    r = await session.execute(
        select(TimeSlot).where(TimeSlot.date == date_str).order_by(TimeSlot.time)
    )
    existing = r.scalars().all()
    existing_times = [s.time for s in existing]

    jalali_label = to_jalali_with_year(date_str)
    existing_text = ""
    if existing_times:
        existing_text = f"\n\n⏰ ساعت‌های ثبت‌شده: <b>{' | '.join(existing_times)}</b>"

    await state.set_state(SlotFSM.times)
    await cb.message.edit_text(
        f"📅 <b>{jalali_label}</b>{existing_text}\n\n"
        f"🕐 ساعت‌های جدید را با کاما وارد کنید:\n"
        f"<i>مثال: 09:00,10:00,11:30,14:00</i>",
        reply_markup=back_btn("adm:slots"), parse_mode="HTML"
    )
    await cb.answer()

@router.message(SlotFSM.times)
async def slot_times(msg: Message, state: FSMContext, session: AsyncSession):
    d = await state.get_data()
    date_str = d["date"]
    raw_times = [t.strip() for t in msg.text.replace("،",",").split(",") if t.strip()]

    valid_times, invalid_times = [], []
    for t in raw_times:
        if validate_time(t):
            # نرمال‌سازی: 9:0 → 09:00
            h, m = t.split(":")
            valid_times.append(f"{int(h):02d}:{int(m):02d}")
        else:
            invalid_times.append(t)

    if not valid_times:
        await msg.answer(
            "❌ هیچ ساعت معتبری وارد نشد.\n"
            "فرمت صحیح: <code>09:00,10:00,11:30</code>",
            parse_mode="HTML"
        ); return

    added, skipped = 0, 0
    for t in valid_times:
        exists = await session.execute(
            select(TimeSlot).where(TimeSlot.date == date_str, TimeSlot.time == t)
        )
        if not exists.scalar_one_or_none():
            session.add(TimeSlot(date=date_str, time=t))
            added += 1
        else:
            skipped += 1
    await session.commit()
    await state.clear()

    jalali_label = to_jalali_with_year(date_str)
    result_text = (
        f"✅ <b>زمان‌بندی ثبت شد</b>\n\n"
        f"📅 {jalali_label}\n"
        f"➕ اضافه شد: <b>{added} ساعت</b>\n"
    )
    if skipped:
        result_text += f"⏭ تکراری (نادیده گرفته شد): <b>{skipped}</b>\n"
    if invalid_times:
        result_text += f"❌ نامعتبر: <b>{', '.join(invalid_times)}</b>\n"
    result_text += f"\n⏰ ساعت‌های ثبت‌شده: <b>{', '.join(sorted(valid_times))}</b>"

    await msg.answer(result_text, reply_markup=back_btn("adm:slots"), parse_mode="HTML")

# ── روزهای تعطیل ─────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:holidays")
async def adm_holidays(cb: CallbackQuery, session: AsyncSession):
    r = await session.execute(select(HolidayDate).order_by(HolidayDate.date))
    holidays = r.scalars().all()
    text = "🎌 <b>روزهای تعطیل</b>\n<i>این روزها در نوبت‌گیری نمایش داده نمی‌شوند</i>"
    await cb.message.edit_text(text, reply_markup=admin_holidays_kb(holidays), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data == "adm:hol:new")
async def adm_hol_new(cb: CallbackQuery, state: FSMContext):
    await state.set_state(HolidayFSM.date)
    # دکمه‌های ۱۴ روز آینده برای تعطیلی هم
    days = next_n_days(14)
    kb = InlineKeyboardBuilder()
    for d in days:
        kb.row(InlineKeyboardButton(
            text=f"📅 {to_jalali_with_year(d)}",
            callback_data=f"adm:hol:pick:{d}"
        ))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="adm:holidays"))
    await cb.message.edit_text(
        "🎌 <b>روز تعطیل را انتخاب کنید:</b>",
        reply_markup=kb.as_markup(), parse_mode="HTML"
    )
    await cb.answer()

@router.callback_query(F.data.startswith("adm:hol:pick:"))
async def adm_hol_pick(cb: CallbackQuery, state: FSMContext):
    date_str = cb.data.split(":")[3]
    await state.update_data(date=date_str)
    await state.set_state(HolidayFSM.label)
    await cb.message.edit_text(
        f"📅 <b>{to_jalali_with_year(date_str)}</b>\n\n"
        f"🏷 عنوان تعطیلی را وارد کنید:\n<i>مثال: عید نوروز</i>",
        reply_markup=back_btn("adm:holidays"), parse_mode="HTML"
    )
    await cb.answer()

@router.message(HolidayFSM.label)
async def hol_label(msg: Message, state: FSMContext, session: AsyncSession):
    d = await state.get_data()
    # بررسی تکراری نبودن
    exists = await session.execute(select(HolidayDate).where(HolidayDate.date == d["date"]))
    if exists.scalar_one_or_none():
        await msg.answer(
            f"⚠️ {to_jalali_with_year(d['date'])} قبلاً به عنوان تعطیل ثبت شده.",
            reply_markup=back_btn("adm:holidays")
        )
        await state.clear(); return
    h = HolidayDate(date=d["date"], label=msg.text.strip())
    session.add(h)
    await session.commit()
    await state.clear()
    await msg.answer(
        f"✅ <b>{to_jalali_with_year(d['date'])}</b> — {h.label}\nبه تعطیلات اضافه شد.",
        reply_markup=back_btn("adm:holidays"), parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("adm:hol:del:"))
async def adm_hol_del(cb: CallbackQuery, session: AsyncSession):
    hol_id = int(cb.data.split(":")[3])
    h = await session.get(HolidayDate, hol_id)
    if not h: await cb.answer("یافت نشد!", show_alert=True); return
    await session.delete(h)
    await session.commit()
    await adm_holidays(cb, session)

# ── تنظیمات ───────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:settings")
async def adm_settings(cb: CallbackQuery):
    await cb.message.edit_text(
        "🔧 <b>تنظیمات</b>",
        reply_markup=admin_settings_kb(config.BOOKING_ENABLED, config.PAYMENT_ENABLED, config.SERVICES_VISIBLE),
        parse_mode="HTML"
    )
    await cb.answer()

@router.callback_query(F.data.startswith("adm:toggle:"))
async def adm_toggle(cb: CallbackQuery):
    key = cb.data.split(":")[2]
    if key == "booking":
        config.BOOKING_ENABLED = not config.BOOKING_ENABLED
        _update_env("BOOKING_ENABLED", str(config.BOOKING_ENABLED).lower())
    elif key == "payment":
        config.PAYMENT_ENABLED = not config.PAYMENT_ENABLED
        _update_env("PAYMENT_ENABLED", str(config.PAYMENT_ENABLED).lower())
    elif key == "services":
        config.SERVICES_VISIBLE = not config.SERVICES_VISIBLE
        _update_env("SERVICES_VISIBLE", str(config.SERVICES_VISIBLE).lower())
    await adm_settings(cb)

@router.callback_query(F.data == "adm:shopinfo")
async def adm_shopinfo(cb: CallbackQuery):
    text = (
        f"🏪 <b>اطلاعات آرایشگاه</b>\n\n"
        f"نام: <b>{config.SHOP_NAME or '—'}</b>\n"
        f"تلفن: <b>{config.SHOP_PHONE or '—'}</b>\n"
        f"آدرس: <b>{config.SHOP_ADDRESS or '—'}</b>\n\n"
        f"💳 کارت: <code>{config.CARD_NUMBER or '—'}</code>\n"
        f"صاحب کارت: <b>{config.CARD_HOLDER or '—'}</b>"
    )
    await cb.message.edit_text(text, reply_markup=admin_shop_info_kb(), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("adm:shop:set:"))
async def adm_shop_set(cb: CallbackQuery, state: FSMContext):
    field = cb.data.split(":")[3]
    labels = {
        "name":"نام آرایشگاه","phone":"شماره تلفن",
        "address":"آدرس","card":"شماره کارت","holder":"نام صاحب کارت"
    }
    await state.update_data(field=field)
    await state.set_state(ShopFSM.value)
    await cb.message.edit_text(
        f"✏️ <b>{labels.get(field, field)} جدید را وارد کنید:</b>",
        reply_markup=back_btn("adm:shopinfo"), parse_mode="HTML"
    )
    await cb.answer()

@router.message(ShopFSM.value)
async def shop_value(msg: Message, state: FSMContext):
    d = await state.get_data()
    field, value = d["field"], msg.text.strip()
    if field == "name":      config.SHOP_NAME = value;    _update_env("SHOP_NAME", value)
    elif field == "phone":   config.SHOP_PHONE = value;   _update_env("SHOP_PHONE", value)
    elif field == "address": config.SHOP_ADDRESS = value; _update_env("SHOP_ADDRESS", value)
    elif field == "card":    config.CARD_NUMBER = value;  _update_env("CARD_NUMBER", value)
    elif field == "holder":  config.CARD_HOLDER = value;  _update_env("CARD_HOLDER", value)
    await state.clear()
    await msg.answer("✅ ذخیره شد.", reply_markup=back_btn("adm:shopinfo"))

# ── آمار ──────────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:stats")
async def adm_stats(cb: CallbackQuery, session: AsyncSession):
    total   = (await session.execute(select(func.count(Booking.id)))).scalar() or 0
    pending = (await session.execute(select(func.count(Booking.id)).where(Booking.status == BookingStatus.PENDING))).scalar() or 0
    confirmed = (await session.execute(select(func.count(Booking.id)).where(Booking.status == BookingStatus.CONFIRMED))).scalar() or 0
    done    = (await session.execute(select(func.count(Booking.id)).where(Booking.status == BookingStatus.DONE))).scalar() or 0
    cancelled = (await session.execute(select(func.count(Booking.id)).where(Booking.status == BookingStatus.CANCELLED))).scalar() or 0
    today   = today_tehran().isoformat()
    today_count = (await session.execute(
        select(func.count(Booking.id)).join(Booking.slot).where(TimeSlot.date == today)
    )).scalar() or 0

    await cb.message.edit_text(
        f"📊 <b>آمار کلی</b>\n\n"
        f"📅 امروز ({to_jalali_full(today)}): <b>{today_count}</b> نوبت\n\n"
        f"کل نوبت‌ها: <b>{total}</b>\n"
        f"⏳ در انتظار: <b>{pending}</b>\n"
        f"✅ تایید شده: <b>{confirmed}</b>\n"
        f"💈 انجام شده: <b>{done}</b>\n"
        f"❌ لغو شده: <b>{cancelled}</b>",
        reply_markup=back_btn("adm:main"), parse_mode="HTML"
    )
    await cb.answer()

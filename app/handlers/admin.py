from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.db.models import (Booking, BookingStatus, Service, TimeSlot,
                            Payment, PaymentStatus)
from app.keyboards.menus import (
    admin_main_kb, admin_booking_kb, admin_payment_kb,
    admin_settings_kb, back_btn
)
from app.config import config
import os

router = Router()

class IsAdmin(Filter):
    async def __call__(self, event) -> bool:
        uid = getattr(event.from_user, "id", None)
        return uid in config.ADMIN_IDS

class ServiceFSM(StatesGroup):
    name = State(); price = State(); duration = State()

class SlotFSM(StatesGroup):
    date = State(); times = State()

class CardFSM(StatesGroup):
    number = State(); holder = State()

router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

# ── پنل اصلی ─────────────────────────────────────────────────────────────────
@router.message(F.text == "⚙️ پنل مدیریت")
async def admin_panel(msg: Message):
    await msg.answer("⚙️ <b>پنل مدیریت</b>", reply_markup=admin_main_kb(), parse_mode="HTML")

@router.callback_query(F.data == "adm:main")
async def adm_main(cb: CallbackQuery):
    await cb.message.edit_text("⚙️ <b>پنل مدیریت</b>", reply_markup=admin_main_kb(), parse_mode="HTML")
    await cb.answer()

# ── نوبت‌ها ───────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:bookings:today")
async def adm_bookings_today(cb: CallbackQuery, session: AsyncSession):
    from datetime import date
    today = date.today().isoformat()
    r = await session.execute(
        select(Booking)
        .join(Booking.slot)
        .where(TimeSlot.date == today)
        .options(selectinload(Booking.user), selectinload(Booking.service), selectinload(Booking.slot))
        .order_by(TimeSlot.time)
    )
    bookings = r.scalars().all()
    if not bookings:
        await cb.message.edit_text("📋 امروز نوبتی ندارید.", reply_markup=back_btn("adm:main"))
        await cb.answer(); return
    S = {"pending":"⏳","confirmed":"✅","cancelled":"❌","done":"💈"}
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    for b in bookings:
        sv = b.status.value if hasattr(b.status,"value") else b.status
        name = b.user.full_name if b.user else "—"
        kb.row(InlineKeyboardButton(
            text=f"{S.get(sv,'📋')} {b.slot.time} — {name} — {b.service.name}",
            callback_data=f"adm:bk:view:{b.id}"
        ))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="adm:main"))
    await cb.message.edit_text(f"📋 <b>نوبت‌های امروز ({today})</b>",
                                reply_markup=kb.as_markup(), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("adm:bk:view:"))
async def adm_bk_view(cb: CallbackQuery, session: AsyncSession):
    bk_id = int(cb.data.split(":")[3])
    r = await session.execute(
        select(Booking).where(Booking.id == bk_id)
        .options(selectinload(Booking.user), selectinload(Booking.service), selectinload(Booking.slot))
    )
    bk = r.scalar_one_or_none()
    if not bk:
        await cb.answer("یافت نشد!", show_alert=True); return
    sv = bk.status.value if hasattr(bk.status,"value") else bk.status
    S = {"pending":"⏳ در انتظار","confirmed":"✅ تایید","cancelled":"❌ لغو","done":"💈 انجام شد"}
    text = (
        f"📋 <b>نوبت #{bk.id}</b>\n"
        f"👤 {bk.user.full_name if bk.user else '—'} (@{bk.user.username or '—' if bk.user else '—'})\n"
        f"✂️ {bk.service.name}  |  {bk.service.price:,} ت\n"
        f"📅 {bk.slot.date}  🕐 {bk.slot.time}\n"
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
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    for p in payments:
        name = p.booking.user.full_name if p.booking and p.booking.user else "—"
        kb.row(InlineKeyboardButton(
            text=f"💳 #{p.id} — {name}",
            callback_data=f"adm:pay:view:{p.id}"
        ))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="adm:main"))
    await cb.message.edit_text("💳 <b>پرداخت‌های معلق:</b>",
                                reply_markup=kb.as_markup(), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("adm:pay:view:"))
async def adm_pay_view(cb: CallbackQuery, session: AsyncSession):
    pay_id = int(cb.data.split(":")[3])
    r = await session.execute(
        select(Payment).where(Payment.id == pay_id)
        .options(selectinload(Payment.booking).selectinload(Booking.user))
    )
    pay = r.scalar_one_or_none()
    if not pay: await cb.answer("یافت نشد!", show_alert=True); return
    name = pay.booking.user.full_name if pay.booking and pay.booking.user else "—"
    await cb.message.answer_photo(
        photo=pay.receipt_file,
        caption=f"💳 رسید پرداخت از {name}\nنوبت #{pay.booking_id}",
        reply_markup=admin_payment_kb(pay.id)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("adm:pay:confirm:"))
async def adm_pay_confirm(cb: CallbackQuery, session: AsyncSession):
    pay_id = int(cb.data.split(":")[3])
    r = await session.execute(
        select(Payment).where(Payment.id == pay_id)
        .options(selectinload(Payment.booking))
    )
    pay = r.scalar_one_or_none()
    if not pay: await cb.answer("یافت نشد!", show_alert=True); return
    pay.status = PaymentStatus.CONFIRMED
    pay.booking.status = BookingStatus.CONFIRMED
    await session.commit()
    try:
        await cb.bot.send_message(
            pay.booking.user_id,
            "✅ <b>پرداخت شما تایید شد!</b>\nنوبتتان قطعی است. منتظرتان هستیم 💈",
            parse_mode="HTML"
        )
    except: pass
    await cb.message.edit_caption("✅ پرداخت تایید شد.")
    await cb.answer()

@router.callback_query(F.data.startswith("adm:pay:reject:"))
async def adm_pay_reject(cb: CallbackQuery, session: AsyncSession):
    pay_id = int(cb.data.split(":")[3])
    r = await session.execute(
        select(Payment).where(Payment.id == pay_id)
        .options(selectinload(Payment.booking))
    )
    pay = r.scalar_one_or_none()
    if not pay: await cb.answer("یافت نشد!", show_alert=True); return
    pay.status = PaymentStatus.REJECTED
    await session.commit()
    try:
        await cb.bot.send_message(
            pay.booking.user_id,
            "❌ <b>رسید پرداخت رد شد.</b>\nلطفاً مجدداً ارسال کنید یا با آرایشگاه تماس بگیرید.",
            parse_mode="HTML"
        )
    except: pass
    await cb.message.edit_caption("❌ پرداخت رد شد.")
    await cb.answer()

# ── خدمات ─────────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:services")
async def adm_services(cb: CallbackQuery, session: AsyncSession):
    r = await session.execute(select(Service).order_by(Service.id))
    services = r.scalars().all()
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    for s in services:
        icon = "🟢" if s.is_active else "🔴"
        kb.row(InlineKeyboardButton(
            text=f"{icon} {s.name} — {s.price:,} ت",
            callback_data=f"adm:svc:toggle:{s.id}"
        ))
    kb.row(InlineKeyboardButton(text="➕ خدمت جدید", callback_data="adm:svc:new"))
    kb.row(InlineKeyboardButton(text="🔙 بازگشت",    callback_data="adm:main"))
    await cb.message.edit_text("✂️ <b>مدیریت خدمات</b>",
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
    await cb.message.edit_text("✂️ نام خدمت جدید:", reply_markup=back_btn("adm:services"))
    await cb.answer()

@router.message(ServiceFSM.name)
async def svc_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await state.set_state(ServiceFSM.price)
    await msg.answer("💰 قیمت (تومان):")

@router.message(ServiceFSM.price)
async def svc_price(msg: Message, state: FSMContext):
    try: price = int(msg.text.replace(",",""))
    except: await msg.answer("❌ عدد وارد کنید:"); return
    await state.update_data(price=price)
    await state.set_state(ServiceFSM.duration)
    await msg.answer("⏱ مدت زمان (دقیقه):")

@router.message(ServiceFSM.duration)
async def svc_duration(msg: Message, state: FSMContext, session: AsyncSession):
    try: dur = int(msg.text)
    except: await msg.answer("❌ عدد وارد کنید:"); return
    d = await state.get_data()
    svc = Service(name=d["name"], price=d["price"], duration=dur)
    session.add(svc)
    await session.commit()
    await state.clear()
    await msg.answer(f"✅ خدمت <b>{svc.name}</b> اضافه شد.", reply_markup=back_btn("adm:services"), parse_mode="HTML")

# ── زمان‌بندی ─────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:slots")
async def adm_slots(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SlotFSM.date)
    await cb.message.edit_text(
        "📅 تاریخ را وارد کنید (مثال: 2026-06-01):",
        reply_markup=back_btn("adm:main")
    )
    await cb.answer()

@router.message(SlotFSM.date)
async def slot_date(msg: Message, state: FSMContext):
    await state.update_data(date=msg.text.strip())
    await state.set_state(SlotFSM.times)
    await msg.answer("🕐 ساعت‌ها را با کاما وارد کنید (مثال: 09:00,10:00,11:00):")

@router.message(SlotFSM.times)
async def slot_times(msg: Message, state: FSMContext, session: AsyncSession):
    d = await state.get_data()
    times = [t.strip() for t in msg.text.split(",") if t.strip()]
    added = 0
    for t in times:
        exists = await session.execute(
            select(TimeSlot).where(TimeSlot.date == d["date"], TimeSlot.time == t)
        )
        if not exists.scalar_one_or_none():
            session.add(TimeSlot(date=d["date"], time=t))
            added += 1
    await session.commit()
    await state.clear()
    await msg.answer(f"✅ {added} زمان برای {d['date']} اضافه شد.", reply_markup=back_btn("adm:slots"))

# ── تنظیمات toggle ────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:settings")
async def adm_settings(cb: CallbackQuery):
    await cb.message.edit_text(
        "🔧 <b>تنظیمات</b>",
        reply_markup=admin_settings_kb(
            config.BOOKING_ENABLED,
            config.PAYMENT_ENABLED,
            config.SERVICES_VISIBLE
        ),
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

def _update_env(key: str, value: str):
    env_path = ".env"
    try:
        lines = open(env_path).readlines() if os.path.exists(env_path) else []
        found = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"{key}={value}\n")
        with open(env_path, "w") as f:
            f.writelines(new_lines)
    except: pass

@router.callback_query(F.data == "adm:set:card")
async def adm_set_card(cb: CallbackQuery, state: FSMContext):
    await state.set_state(CardFSM.number)
    await cb.message.edit_text("💳 شماره کارت جدید:", reply_markup=back_btn("adm:settings"))
    await cb.answer()

@router.message(CardFSM.number)
async def card_number(msg: Message, state: FSMContext):
    await state.update_data(number=msg.text.strip())
    await state.set_state(CardFSM.holder)
    await msg.answer("👤 نام صاحب کارت:")

@router.message(CardFSM.holder)
async def card_holder(msg: Message, state: FSMContext):
    d = await state.get_data()
    config.CARD_NUMBER = d["number"]
    config.CARD_HOLDER = msg.text.strip()
    _update_env("CARD_NUMBER", config.CARD_NUMBER)
    _update_env("CARD_HOLDER", config.CARD_HOLDER)
    await state.clear()
    await msg.answer(f"✅ کارت به‌روز شد:\n<code>{config.CARD_NUMBER}</code> — {config.CARD_HOLDER}",
                     reply_markup=back_btn("adm:settings"), parse_mode="HTML")

# ── آمار ──────────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:stats")
async def adm_stats(cb: CallbackQuery, session: AsyncSession):
    total   = (await session.execute(select(func.count(Booking.id)))).scalar() or 0
    pending = (await session.execute(select(func.count(Booking.id)).where(Booking.status == BookingStatus.PENDING))).scalar() or 0
    done    = (await session.execute(select(func.count(Booking.id)).where(Booking.status == BookingStatus.DONE))).scalar() or 0
    await cb.message.edit_text(
        f"📊 <b>آمار</b>\n\n"
        f"کل نوبت‌ها: <b>{total}</b>\n"
        f"در انتظار: <b>{pending}</b>\n"
        f"انجام شده: <b>{done}</b>",
        reply_markup=back_btn("adm:main"), parse_mode="HTML"
    )
    await cb.answer()

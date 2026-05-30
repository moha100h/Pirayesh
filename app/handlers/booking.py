from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.models import Service, TimeSlot, Booking, User, BookingStatus, HolidayDate
from app.keyboards.menus import (
    services_kb, slots_kb, back_btn,
    my_bookings_kb, booking_detail_kb,
    admin_booking_notify_kb, payment_kb
)
from app.services.jalali import (
    to_jalali_full, to_jalali_with_year,
    next_3_days, fmt_price, today_tehran
)
from app.config import config

router = Router()

class BookingFSM(StatesGroup):
    choose_service = State()
    choose_date    = State()
    choose_slot    = State()
    confirm        = State()

async def _check_registered(event, session: AsyncSession) -> bool:
    uid = event.from_user.id
    u = await session.get(User, uid)
    if not u or not u.registered:
        text = "⚠️ ابتدا باید ثبت‌نام کنید. دستور /start را بزنید."
        if isinstance(event, Message): await event.answer(text)
        else: await event.message.answer(text); await event.answer()
        return False
    return True

@router.message(F.text == "📅 نوبت‌گیری")
async def start_booking(msg: Message, session: AsyncSession, state: FSMContext):
    if not config.BOOKING_ENABLED:
        await msg.answer("⚠️ نوبت‌گیری در حال حاضر غیرفعال است."); return
    if not await _check_registered(msg, session): return
    r = await session.execute(select(Service).where(Service.is_active == True).order_by(Service.id))
    services = r.scalars().all()
    if not services:
        await msg.answer("⚠️ هیچ خدمات فعالی وجود ندارد."); return
    await state.set_state(BookingFSM.choose_service)
    await msg.answer("✂️ <b>خدمت مورد نظر را انتخاب کنید:</b>",
                     reply_markup=services_kb(services), parse_mode="HTML")

@router.callback_query(F.data.startswith("book:svc:"))
async def choose_service(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    svc_id = int(cb.data.split(":")[2])
    svc = await session.get(Service, svc_id)
    if not svc: await cb.answer("خدمت یافت نشد!", show_alert=True); return
    await state.update_data(service_id=svc_id, service_name=svc.name, price=svc.price)

    days = next_3_days()
    # تعطیلات فعال
    r_hol = await session.execute(
        select(HolidayDate).where(HolidayDate.is_active == True)
    )
    active_holidays = {h.date: h.label for h in r_hol.scalars().all()}

    r_slots = await session.execute(
        select(TimeSlot.date).where(TimeSlot.is_booked == False).distinct()
    )
    available_dates = {row[0] for row in r_slots.all()}

    kb = InlineKeyboardBuilder()
    has_any = False
    for d in days:
        if d in active_holidays:
            # روز تعطیل — نمایش می‌شه ولی غیرقابل انتخاب
            kb.row(InlineKeyboardButton(
                text=f"🎌 {to_jalali_with_year(d)} — {active_holidays[d]} (تعطیل)",
                callback_data=f"book:holiday:{d}"
            ))
            has_any = True
        elif d in available_dates:
            kb.row(InlineKeyboardButton(
                text=f"📅 {to_jalali_with_year(d)}",
                callback_data=f"book:date:{d}:{svc_id}"
            ))
            has_any = True

    if not has_any:
        await cb.message.edit_text(
            "⚠️ در ۳ روز آینده زمان خالی موجود نیست.\nلطفاً بعداً مراجعه کنید.",
            reply_markup=back_btn("nav:main")
        )
        await cb.answer(); return

    kb.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="book:back:svc"))
    await state.set_state(BookingFSM.choose_date)
    await cb.message.edit_text(
        f"📅 <b>روز مورد نظر را انتخاب کنید:</b>\n"
        f"<i>✂️ {svc.name}  |  {fmt_price(svc.price)}</i>",
        reply_markup=kb.as_markup(), parse_mode="HTML"
    )
    await cb.answer()

@router.callback_query(F.data.startswith("book:holiday:"))
async def book_holiday(cb: CallbackQuery):
    await cb.answer("🎌 این روز تعطیل است. لطفاً روز دیگری انتخاب کنید.", show_alert=True)

@router.callback_query(F.data.startswith("book:date:"))
async def choose_date(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    parts = cb.data.split(":")
    date_str, svc_id = parts[2], int(parts[3])
    await state.update_data(date=date_str)
    r = await session.execute(
        select(TimeSlot).where(TimeSlot.date == date_str, TimeSlot.is_booked == False)
        .order_by(TimeSlot.time)
    )
    slots = r.scalars().all()
    if not slots:
        await cb.message.edit_text("⚠️ این روز زمان خالی ندارد.", reply_markup=back_btn("book:back:svc"))
        await cb.answer(); return
    await state.set_state(BookingFSM.choose_slot)
    await cb.message.edit_text(
        f"🕐 <b>ساعت مورد نظر را انتخاب کنید:</b>\n"
        f"<i>📅 {to_jalali_with_year(date_str)}</i>",
        reply_markup=slots_kb(slots, svc_id), parse_mode="HTML"
    )
    await cb.answer()

@router.callback_query(F.data.startswith("book:slot:"))
async def choose_slot(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    parts = cb.data.split(":")
    slot_id, svc_id = int(parts[2]), int(parts[3])
    slot = await session.get(TimeSlot, slot_id)
    if not slot or slot.is_booked:
        await cb.answer("این زمان رزرو شده!", show_alert=True); return
    d = await state.get_data()
    await state.update_data(slot_id=slot_id)
    text = (
        f"📋 <b>تایید نوبت</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✂️ خدمت: <b>{d['service_name']}</b>\n"
        f"📅 تاریخ: <b>{to_jalali_with_year(slot.date)}</b>\n"
        f"🕐 ساعت: <b>{slot.time}</b>\n"
        f"💰 مبلغ: <b>{fmt_price(d['price'])}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"آیا این نوبت را تایید می‌کنید؟"
    )
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ تایید نوبت", callback_data=f"book:confirm:{slot_id}:{svc_id}"),
        InlineKeyboardButton(text="❌ انصراف",     callback_data="nav:main")
    )
    await state.set_state(BookingFSM.confirm)
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("book:confirm:"))
async def confirm_booking(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    parts = cb.data.split(":")
    slot_id, svc_id = int(parts[2]), int(parts[3])
    slot = await session.get(TimeSlot, slot_id)
    if not slot or slot.is_booked:
        await cb.answer("این زمان رزرو شده!", show_alert=True); return
    d = await state.get_data()
    u = await session.get(User, cb.from_user.id)
    booking = Booking(
        user_id=cb.from_user.id, service_id=d["service_id"],
        slot_id=slot_id, status=BookingStatus.PENDING
    )
    slot.is_booked = True
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    await state.clear()

    for admin_id in config.ADMIN_IDS:
        try:
            await cb.bot.send_message(
                admin_id,
                f"🔔 <b>نوبت جدید ثبت شد</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>{u.full_name}</b>\n"
                f"📞 {u.phone}\n"
                f"📱 @{u.username or '—'}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✂️ {d['service_name']}\n"
                f"📅 {to_jalali_with_year(slot.date)}\n"
                f"🕐 ساعت: {slot.time}\n"
                f"💰 {fmt_price(d['price'])}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🆔 نوبت #{booking.id}",
                reply_markup=admin_booking_notify_kb(booking.id),
                parse_mode="HTML"
            )
        except: pass

    summary = (
        f"✅ <b>نوبت شما ثبت شد!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✂️ خدمت: <b>{d['service_name']}</b>\n"
        f"📅 تاریخ: <b>{to_jalali_with_year(slot.date)}</b>\n"
        f"🕐 ساعت: <b>{slot.time}</b>\n"
        f"💰 مبلغ: <b>{fmt_price(d['price'])}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )
    if config.PAYMENT_ENABLED and config.CARD_NUMBER:
        summary += (
            f"💳 برای تایید نهایی مبلغ را به کارت زیر واریز کنید:\n"
            f"<code>{config.CARD_NUMBER}</code>\n"
            f"به نام: <b>{config.CARD_HOLDER}</b>"
        )
    else:
        summary += "پرداخت به صورت حضوری انجام می‌شود."

    await cb.message.edit_text(summary, reply_markup=payment_kb(booking.id), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("book:back:"))
async def book_back(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.clear()
    r = await session.execute(select(Service).where(Service.is_active == True))
    services = r.scalars().all()
    await cb.message.edit_text("✂️ <b>خدمت مورد نظر را انتخاب کنید:</b>",
                                reply_markup=services_kb(services), parse_mode="HTML")
    await cb.answer()

@router.message(F.text == "📋 نوبت‌های من")
async def my_bookings(msg: Message, session: AsyncSession):
    r = await session.execute(
        select(Booking).where(Booking.user_id == msg.from_user.id)
        .options(selectinload(Booking.service), selectinload(Booking.slot))
        .order_by(Booking.id.desc())
    )
    bookings = r.scalars().all()
    active = [b for b in bookings if b.status.value in ("pending","confirmed")]
    if not active:
        await msg.answer("📋 نوبت فعالی ندارید."); return
    await msg.answer("📋 <b>نوبت‌های فعال شما:</b>",
                     reply_markup=my_bookings_kb(active), parse_mode="HTML")

@router.callback_query(F.data == "mybk:list")
async def mybk_list(cb: CallbackQuery, session: AsyncSession):
    r = await session.execute(
        select(Booking).where(Booking.user_id == cb.from_user.id)
        .options(selectinload(Booking.service), selectinload(Booking.slot))
        .order_by(Booking.id.desc())
    )
    bookings = r.scalars().all()
    active = [b for b in bookings if b.status.value in ("pending","confirmed")]
    if not active:
        await cb.message.edit_text("📋 نوبت فعالی ندارید."); await cb.answer(); return
    await cb.message.edit_text("📋 <b>نوبت‌های فعال شما:</b>",
                                reply_markup=my_bookings_kb(active), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("mybk:view:"))
async def mybk_view(cb: CallbackQuery, session: AsyncSession):
    bk_id = int(cb.data.split(":")[2])
    r = await session.execute(
        select(Booking).where(Booking.id == bk_id)
        .options(selectinload(Booking.service), selectinload(Booking.slot))
    )
    bk = r.scalar_one_or_none()
    if not bk: await cb.answer("یافت نشد!", show_alert=True); return
    S = {"pending":"⏳ در انتظار تایید","confirmed":"✅ تایید شده",
         "cancelled":"❌ لغو شده","done":"💈 انجام شد"}
    sv = bk.status.value if hasattr(bk.status,"value") else bk.status
    text = (
        f"📋 <b>جزئیات نوبت #{bk.id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✂️ {bk.service.name}\n"
        f"📅 {to_jalali_with_year(bk.slot.date)}\n"
        f"🕐 ساعت: {bk.slot.time}\n"
        f"💰 {fmt_price(bk.service.price)}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"وضعیت: {S.get(sv, sv)}"
    )
    await cb.message.edit_text(text, reply_markup=booking_detail_kb(bk.id, sv), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("mybk:cancel:"))
async def mybk_cancel(cb: CallbackQuery, session: AsyncSession):
    bk_id = int(cb.data.split(":")[2])
    r = await session.execute(
        select(Booking).where(Booking.id == bk_id).options(selectinload(Booking.slot))
    )
    bk = r.scalar_one_or_none()
    if not bk: await cb.answer("یافت نشد!", show_alert=True); return
    bk.status = BookingStatus.CANCELLED
    bk.slot.is_booked = False
    await session.commit()
    await cb.message.edit_text("❌ نوبت شما لغو شد.")
    for admin_id in config.ADMIN_IDS:
        try:
            await cb.bot.send_message(admin_id,
                f"⚠️ <b>نوبت #{bk_id} توسط کاربر لغو شد</b>", parse_mode="HTML")
        except: pass
    await cb.answer()

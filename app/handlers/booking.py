from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.models import Service, TimeSlot, Booking, User, BookingStatus
from app.keyboards.menus import (
    services_kb, dates_kb, slots_kb,
    confirm_booking_kb, payment_kb, my_bookings_kb,
    booking_detail_kb, back_btn
)
from app.config import config

router = Router()

class BookingFSM(StatesGroup):
    choose_service = State()
    choose_date    = State()
    choose_slot    = State()
    confirm        = State()

# ── نوبت‌گیری ─────────────────────────────────────────────────────────────────
@router.message(F.text == "📅 نوبت‌گیری")
async def start_booking(msg: Message, session: AsyncSession, state: FSMContext):
    if not config.BOOKING_ENABLED:
        await msg.answer("⚠️ نوبت‌گیری در حال حاضر غیرفعال است.")
        return
    r = await session.execute(select(Service).where(Service.is_active == True))
    services = r.scalars().all()
    if not services:
        await msg.answer("⚠️ هیچ خدمات فعالی وجود ندارد.")
        return
    await state.set_state(BookingFSM.choose_service)
    await msg.answer("✂️ <b>خدمت مورد نظر را انتخاب کنید:</b>",
                     reply_markup=services_kb(services), parse_mode="HTML")

@router.callback_query(F.data.startswith("book:svc:"))
async def choose_service(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    svc_id = int(cb.data.split(":")[2])
    svc = await session.get(Service, svc_id)
    if not svc:
        await cb.answer("خدمت یافت نشد!", show_alert=True); return
    await state.update_data(service_id=svc_id, service_name=svc.name, price=svc.price)
    # تاریخ‌های موجود
    r = await session.execute(
        select(TimeSlot.date).where(TimeSlot.is_booked == False).distinct()
    )
    dates = sorted([row[0] for row in r.all()])
    if not dates:
        await cb.message.edit_text("⚠️ هیچ زمان خالی‌ای موجود نیست.")
        await cb.answer(); return
    await state.set_state(BookingFSM.choose_date)
    await cb.message.edit_text("📅 <b>روز مورد نظر را انتخاب کنید:</b>",
                                reply_markup=dates_kb(dates, svc_id), parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("book:date:"))
async def choose_date(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    parts = cb.data.split(":")
    date, svc_id = parts[2], int(parts[3])
    await state.update_data(date=date)
    r = await session.execute(
        select(TimeSlot).where(TimeSlot.date == date, TimeSlot.is_booked == False)
        .order_by(TimeSlot.time)
    )
    slots = r.scalars().all()
    if not slots:
        await cb.message.edit_text("⚠️ این روز زمان خالی ندارد.")
        await cb.answer(); return
    await state.set_state(BookingFSM.choose_slot)
    await cb.message.edit_text(f"🕐 <b>ساعت مورد نظر در {date}:</b>",
                                reply_markup=slots_kb(slots, svc_id), parse_mode="HTML")
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
        f"📋 <b>تایید نوبت</b>\n\n"
        f"✂️ خدمت: <b>{d['service_name']}</b>\n"
        f"📅 تاریخ: <b>{slot.date}</b>\n"
        f"🕐 ساعت: <b>{slot.time}</b>\n"
        f"💰 مبلغ: <b>{d['price']:,} تومان</b>"
    )
    await state.set_state(BookingFSM.confirm)
    await cb.message.edit_text(text, reply_markup=confirm_booking_kb(slot_id, svc_id),
                                parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("book:confirm:"))
async def confirm_booking(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    parts = cb.data.split(":")
    slot_id, svc_id = int(parts[2]), int(parts[3])
    slot = await session.get(TimeSlot, slot_id)
    if not slot or slot.is_booked:
        await cb.answer("این زمان رزرو شده!", show_alert=True); return
    d = await state.get_data()
    booking = Booking(
        user_id=cb.from_user.id,
        service_id=d["service_id"],
        slot_id=slot_id,
        status=BookingStatus.PENDING,
    )
    slot.is_booked = True
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    await state.clear()
    # اطلاع به ادمین
    for admin_id in config.ADMIN_IDS:
        try:
            await cb.bot.send_message(
                admin_id,
                f"🔔 <b>نوبت جدید</b>\n"
                f"👤 {cb.from_user.full_name} (@{cb.from_user.username or '—'})\n"
                f"✂️ {d['service_name']}  |  {slot.date} {slot.time}\n"
                f"💰 {d['price']:,} تومان\n"
                f"/bk_{booking.id}",
                parse_mode="HTML"
            )
        except: pass
    if config.PAYMENT_ENABLED and config.CARD_NUMBER:
        await cb.message.edit_text(
            f"✅ <b>نوبت ثبت شد!</b>\n\n"
            f"💳 برای تایید نهایی، مبلغ <b>{d['price']:,} تومان</b> را به کارت زیر واریز کنید:\n"
            f"<code>{config.CARD_NUMBER}</code>  —  {config.CARD_HOLDER}\n\n"
            f"سپس رسید را ارسال کنید.",
            reply_markup=payment_kb(booking.id), parse_mode="HTML"
        )
    else:
        await cb.message.edit_text(
            f"✅ <b>نوبت ثبت شد!</b>\n"
            f"📅 {slot.date}  🕐 {slot.time}\n"
            f"پرداخت به صورت حضوری انجام می‌شود.",
            parse_mode="HTML"
        )
    await cb.answer()

@router.callback_query(F.data.startswith("book:back:"))
async def book_back(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.clear()
    r = await session.execute(select(Service).where(Service.is_active == True))
    services = r.scalars().all()
    await cb.message.edit_text("✂️ <b>خدمت مورد نظر را انتخاب کنید:</b>",
                                reply_markup=services_kb(services), parse_mode="HTML")
    await cb.answer()

# ── نوبت‌های من ───────────────────────────────────────────────────────────────
@router.message(F.text == "📋 نوبت‌های من")
async def my_bookings(msg: Message, session: AsyncSession):
    r = await session.execute(
        select(Booking)
        .where(Booking.user_id == msg.from_user.id)
        .options(
            selectinload(Booking.service),
            selectinload(Booking.slot),
        )
        .order_by(Booking.id.desc())
    )
    bookings = r.scalars().all()
    active = [b for b in bookings if b.status.value in ("pending","confirmed")]
    if not active:
        await msg.answer("📋 نوبت فعالی ندارید.", reply_markup=back_btn())
        return
    await msg.answer("📋 <b>نوبت‌های فعال شما:</b>",
                     reply_markup=my_bookings_kb(active), parse_mode="HTML")

@router.callback_query(F.data == "mybk:list")
async def mybk_list(cb: CallbackQuery, session: AsyncSession):
    from sqlalchemy.orm import selectinload
    r = await session.execute(
        select(Booking)
        .where(Booking.user_id == cb.from_user.id)
        .options(selectinload(Booking.service), selectinload(Booking.slot))
        .order_by(Booking.id.desc())
    )
    bookings = r.scalars().all()
    active = [b for b in bookings if b.status.value in ("pending","confirmed")]
    if not active:
        await cb.message.edit_text("📋 نوبت فعالی ندارید.")
        await cb.answer(); return
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
    if not bk:
        await cb.answer("یافت نشد!", show_alert=True); return
    S = {"pending":"⏳ در انتظار","confirmed":"✅ تایید شده","cancelled":"❌ لغو","done":"💈 انجام شد"}
    sv = bk.status.value if hasattr(bk.status,"value") else bk.status
    text = (
        f"📋 <b>جزئیات نوبت</b>\n\n"
        f"✂️ {bk.service.name}\n"
        f"📅 {bk.slot.date}  🕐 {bk.slot.time}\n"
        f"💰 {bk.service.price:,} تومان\n"
        f"وضعیت: {S.get(sv, sv)}"
    )
    await cb.message.edit_text(text, reply_markup=booking_detail_kb(bk.id, sv),
                                parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("mybk:cancel:"))
async def mybk_cancel(cb: CallbackQuery, session: AsyncSession):
    bk_id = int(cb.data.split(":")[2])
    r = await session.execute(
        select(Booking).where(Booking.id == bk_id)
        .options(selectinload(Booking.slot))
    )
    bk = r.scalar_one_or_none()
    if not bk:
        await cb.answer("یافت نشد!", show_alert=True); return
    bk.status = BookingStatus.CANCELLED
    bk.slot.is_booked = False
    await session.commit()
    await cb.message.edit_text("❌ نوبت شما لغو شد.")
    for admin_id in config.ADMIN_IDS:
        try:
            await cb.bot.send_message(
                admin_id,
                f"⚠️ نوبت #{bk_id} توسط کاربر لغو شد.",
                parse_mode="HTML"
            )
        except: pass
    await cb.answer()

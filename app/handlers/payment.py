from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.models import Booking, Payment, PaymentStatus, BookingStatus, User, Service, TimeSlot
from app.keyboards.menus import back_btn, admin_payment_notify_kb
from app.services.jalali import to_jalali_full, fmt_price
from app.config import config

router = Router()

class PayFSM(StatesGroup):
    waiting_receipt = State()

@router.callback_query(F.data.startswith("pay:send:"))
async def pay_send(cb: CallbackQuery, state: FSMContext):
    bk_id = int(cb.data.split(":")[2])
    await state.update_data(booking_id=bk_id)
    await state.set_state(PayFSM.waiting_receipt)
    await cb.message.edit_text(
        f"📸 <b>ارسال رسید پرداخت</b>\n\n"
        f"💳 شماره کارت:\n<code>{config.CARD_NUMBER}</code>\n"
        f"👤 به نام: <b>{config.CARD_HOLDER}</b>\n\n"
        f"تصویر رسید را ارسال کنید:",
        parse_mode="HTML"
    )
    await cb.answer()

@router.message(PayFSM.waiting_receipt, F.photo)
async def receipt_received(msg: Message, state: FSMContext, session: AsyncSession):
    d = await state.get_data()
    bk_id = d["booking_id"]
    file_id = msg.photo[-1].file_id

    # ذخیره رسید
    pay = Payment(booking_id=bk_id, status=PaymentStatus.SUBMITTED, receipt_file=file_id)
    session.add(pay)
    await session.commit()
    await session.refresh(pay)
    await state.clear()

    # اطلاعات نوبت برای نوتیف
    r = await session.execute(
        select(Booking).where(Booking.id == bk_id)
        .options(selectinload(Booking.user), selectinload(Booking.service), selectinload(Booking.slot))
    )
    bk = r.scalar_one_or_none()
    u = bk.user if bk else None

    await msg.answer(
        "✅ <b>رسید شما دریافت شد.</b>\n"
        "پس از بررسی توسط مدیریت، نتیجه به شما اطلاع داده می‌شود.",
        reply_markup=back_btn(), parse_mode="HTML"
    )

    # نوتیف ادمین — فقط متن حرفه‌ای + دکمه مشاهده رسید
    for admin_id in config.ADMIN_IDS:
        try:
            await msg.bot.send_message(
                admin_id,
                f"💳 <b>واریزی جدید دریافت شد</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>{u.full_name if u else '—'}</b>\n"
                f"📞 {u.phone if u else '—'}\n"
                f"✂️ {bk.service.name if bk else '—'}\n"
                f"📅 {to_jalali_full(bk.slot.date) if bk else '—'}  🕐 {bk.slot.time if bk else '—'}\n"
                f"💰 {fmt_price(bk.service.price) if bk else '—'}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🆔 پرداخت #{pay.id}  |  نوبت #{bk_id}",
                reply_markup=admin_payment_notify_kb(pay.id),
                parse_mode="HTML"
            )
        except: pass

@router.callback_query(F.data.startswith("pay:cash:"))
async def pay_cash(cb: CallbackQuery, session: AsyncSession):
    bk_id = int(cb.data.split(":")[2])
    await cb.message.edit_text(
        "✅ <b>نوبت شما ثبت شد.</b>\n"
        "پرداخت به صورت حضوری در روز مراجعه انجام می‌شود.\n"
        "منتظرتان هستیم 💈",
        parse_mode="HTML"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await cb.bot.send_message(admin_id,
                f"💵 <b>پرداخت حضوری</b>\nنوبت #{bk_id}", parse_mode="HTML")
        except: pass
    await cb.answer()

# ── مشاهده رسید توسط ادمین ───────────────────────────────────────────────────
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

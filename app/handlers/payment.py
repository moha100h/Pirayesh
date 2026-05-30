from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.models import Booking, Payment, PaymentStatus, BookingStatus
from app.keyboards.menus import back_btn, admin_payment_notify_kb
from app.services.jalali import to_jalali_with_year, fmt_price
from app.config import config

router = Router()

class PayFSM(StatesGroup):
    waiting_receipt = State()

# ── ارسال رسید پس از رزرو (اگه کاربر از صفحه نوبت‌های من اقدام کنه) ──────────
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

    pay = Payment(booking_id=bk_id, status=PaymentStatus.SUBMITTED, receipt_file=file_id)
    session.add(pay)
    await session.commit()
    await session.refresh(pay)
    await state.clear()

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

    for admin_id in config.ADMIN_IDS:
        try:
            await msg.bot.send_message(
                admin_id,
                f"💳 <b>رسید واریز جدید</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>{u.full_name if u else '—'}</b>\n"
                f"📞 {u.phone if u else '—'}\n"
                f"✂️ {bk.service.name if bk else '—'}\n"
                f"📅 {to_jalali_with_year(bk.slot.date) if bk else '—'}  🕐 {bk.slot.time if bk else '—'}\n"
                f"💰 {fmt_price(bk.service.price) if bk else '—'}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🆔 پرداخت #{pay.id}  |  نوبت #{bk_id}",
                reply_markup=admin_payment_notify_kb(pay.id),
                parse_mode="HTML"
            )
        except: pass

@router.message(PayFSM.waiting_receipt, ~F.photo)
async def receipt_not_photo(msg: Message):
    await msg.answer("📸 لطفاً <b>تصویر</b> رسید را ارسال کنید.", parse_mode="HTML")

@router.callback_query(F.data.startswith("pay:cash:"))
async def pay_cash(cb: CallbackQuery):
    """پرداخت حضوری — فقط تایید به کاربر (رزرو قبلاً ثبت شده)"""
    await cb.message.edit_text(
        "✅ <b>نوبت شما ثبت شد.</b>\n"
        "پرداخت به صورت حضوری در روز مراجعه انجام می‌شود.\n"
        "منتظرتان هستیم 💈",
        parse_mode="HTML"
    )
    await cb.answer()

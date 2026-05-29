from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.models import Booking, Payment, PaymentStatus, BookingStatus
from app.keyboards.menus import back_btn
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
        f"📸 لطفاً تصویر رسید پرداخت را ارسال کنید.\n"
        f"💳 کارت: <code>{config.CARD_NUMBER}</code>  —  {config.CARD_HOLDER}",
        parse_mode="HTML"
    )
    await cb.answer()

@router.message(PayFSM.waiting_receipt, F.photo)
async def receipt_received(msg: Message, state: FSMContext, session: AsyncSession):
    d = await state.get_data()
    bk_id = d["booking_id"]
    file_id = msg.photo[-1].file_id
    pay = Payment(
        booking_id=bk_id,
        status=PaymentStatus.SUBMITTED,
        receipt_file=file_id,
    )
    session.add(pay)
    await session.commit()
    await session.refresh(pay)
    await state.clear()
    await msg.answer("✅ رسید دریافت شد. پس از تایید ادمین اطلاع‌رسانی می‌شود.",
                     reply_markup=back_btn())
    # اطلاع به ادمین
    for admin_id in config.ADMIN_IDS:
        try:
            await msg.bot.send_photo(
                admin_id,
                photo=file_id,
                caption=(
                    f"💳 <b>رسید پرداخت جدید</b>\n"
                    f"👤 {msg.from_user.full_name} (@{msg.from_user.username or '—'})\n"
                    f"نوبت #{bk_id}\n"
                    f"/pay_{pay.id}"
                ),
                parse_mode="HTML"
            )
        except: pass

@router.callback_query(F.data.startswith("pay:cash:"))
async def pay_cash(cb: CallbackQuery, session: AsyncSession):
    bk_id = int(cb.data.split(":")[2])
    await cb.message.edit_text(
        "✅ نوبت شما ثبت شد.\nپرداخت به صورت حضوری در روز مراجعه انجام می‌شود.",
        parse_mode="HTML"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await cb.bot.send_message(
                admin_id,
                f"💵 نوبت #{bk_id} — پرداخت حضوری انتخاب شد.",
                parse_mode="HTML"
            )
        except: pass
    await cb.answer()

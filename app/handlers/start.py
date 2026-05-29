from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User
from app.keyboards.menus import main_menu, back_btn
from app.config import config

router = Router()

class RegisterFSM(StatesGroup):
    first_name = State()
    last_name  = State()
    phone      = State()

@router.message(CommandStart())
async def cmd_start(msg: Message, session: AsyncSession, state: FSMContext):
    u = await session.get(User, msg.from_user.id)
    if not u:
        u = User(id=msg.from_user.id, username=msg.from_user.username)
        session.add(u)
        await session.commit()
    if not u.registered:
        await state.set_state(RegisterFSM.first_name)
        await msg.answer(
            f"✂️ به ربات <b>{config.SHOP_NAME}</b> خوش آمدید!\n\n"
            f"برای شروع، لطفاً اطلاعات خود را وارد کنید.\n\n"
            f"👤 <b>نام:</b>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    await _show_main(msg, session)

@router.message(RegisterFSM.first_name)
async def reg_first(msg: Message, state: FSMContext):
    await state.update_data(first_name=msg.text.strip())
    await state.set_state(RegisterFSM.last_name)
    await msg.answer("👤 <b>نام خانوادگی:</b>", parse_mode="HTML")

@router.message(RegisterFSM.last_name)
async def reg_last(msg: Message, state: FSMContext):
    await state.update_data(last_name=msg.text.strip())
    await state.set_state(RegisterFSM.phone)
    await msg.answer(
        "📞 <b>شماره تماس:</b>\n<i>(مثال: 09123456789)</i>",
        parse_mode="HTML"
    )

@router.message(RegisterFSM.phone)
async def reg_phone(msg: Message, state: FSMContext, session: AsyncSession):
    phone = msg.text.strip()
    if not phone.startswith("09") or len(phone) != 11 or not phone.isdigit():
        await msg.answer("❌ شماره تماس معتبر نیست. مثال: <code>09123456789</code>", parse_mode="HTML")
        return
    d = await state.get_data()
    u = await session.get(User, msg.from_user.id)
    u.first_name = d["first_name"]
    u.last_name  = d["last_name"]
    u.full_name  = f"{d['first_name']} {d['last_name']}"
    u.phone      = phone
    u.registered = True
    await session.commit()
    await state.clear()
    await msg.answer(
        f"✅ <b>ثبت‌نام با موفقیت انجام شد!</b>\n\n"
        f"خوش آمدید، <b>{u.full_name}</b> عزیز 🙏",
        parse_mode="HTML"
    )
    await _show_main(msg, session)

async def _show_main(msg: Message, session: AsyncSession):
    is_admin = msg.from_user.id in config.ADMIN_IDS
    await msg.answer(
        f"✂️ <b>{config.SHOP_NAME}</b>\nاز منوی زیر انتخاب کنید:",
        reply_markup=main_menu(
            is_admin=is_admin,
            booking=config.BOOKING_ENABLED,
            services=config.SERVICES_VISIBLE,
            payment=config.PAYMENT_ENABLED,
        ),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "nav:main")
async def nav_main(cb: CallbackQuery, session: AsyncSession):
    is_admin = cb.from_user.id in config.ADMIN_IDS
    try: await cb.message.delete()
    except: pass
    await cb.message.answer(
        f"✂️ <b>{config.SHOP_NAME}</b> — منوی اصلی",
        reply_markup=main_menu(
            is_admin=is_admin,
            booking=config.BOOKING_ENABLED,
            services=config.SERVICES_VISIBLE,
            payment=config.PAYMENT_ENABLED,
        ),
        parse_mode="HTML"
    )
    await cb.answer()

@router.message(F.text == "📞 اطلاعات آرایشگاه")
async def shop_info(msg: Message):
    text = (
        f"🏪 <b>{config.SHOP_NAME}</b>\n"
        f"📍 {config.SHOP_ADDRESS or '—'}\n"
        f"📞 {config.SHOP_PHONE or '—'}"
    )
    await msg.answer(text, parse_mode="HTML")

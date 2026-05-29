from aiogram import Router, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User
from app.keyboards.menus import main_menu
from app.config import config

router = Router()

class RegFSM(StatesGroup):
    full_name = State()
    phone     = State()

@router.message(CommandStart())
async def cmd_start(msg: Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    user = await session.get(User, msg.from_user.id)
    if user and user.registered:
        is_admin = msg.from_user.id in config.ADMIN_IDS
        await msg.answer(
            f"👋 خوش اومدی <b>{user.full_name}</b>!",
            reply_markup=main_menu(is_admin=is_admin,
                                   booking=config.BOOKING_ENABLED,
                                   services=config.SERVICES_VISIBLE),
            parse_mode="HTML"
        )
        return

    # ذخیره شماره تلگرام (username یا id)
    tg_username = msg.from_user.username or str(msg.from_user.id)
    await state.update_data(tg_username=tg_username, tg_id=msg.from_user.id)

    await msg.answer(
        f"👋 سلام!\n\n"
        f"📱 شماره تلگرام شما: <code>@{tg_username}</code>\n\n"
        f"لطفاً <b>نام و نام خانوادگی</b> خود را وارد کنید:\n"
        f"<i>(مثال: علی رضایی)</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RegFSM.full_name)

@router.message(RegFSM.full_name)
async def reg_full_name(msg: Message, state: FSMContext):
    name = msg.text.strip()
    if len(name) < 3:
        await msg.answer("❌ نام باید حداقل ۳ حرف باشد. دوباره وارد کنید:"); return
    await state.update_data(full_name=name)

    # دکمه اشتراک‌گذاری شماره
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 اشتراک‌گذاری شماره", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await msg.answer(
        f"✅ <b>{name}</b>\n\n"
        f"حالا شماره تماس خود را وارد کنید یا از دکمه زیر استفاده کنید:",
        reply_markup=kb, parse_mode="HTML"
    )
    await state.set_state(RegFSM.phone)

@router.message(RegFSM.phone, F.contact)
async def reg_phone_contact(msg: Message, state: FSMContext, session: AsyncSession):
    phone = msg.contact.phone_number
    if not phone.startswith("+"): phone = "+" + phone
    await _finish_reg(msg, state, session, phone)

@router.message(RegFSM.phone, F.text)
async def reg_phone_text(msg: Message, state: FSMContext, session: AsyncSession):
    phone = msg.text.strip().replace(" ", "")
    if not (phone.startswith("09") or phone.startswith("+98")) or len(phone) < 10:
        await msg.answer("❌ شماره معتبر نیست. مثال: 09123456789"); return
    await _finish_reg(msg, state, session, phone)

async def _finish_reg(msg: Message, state: FSMContext, session: AsyncSession, phone: str):
    d = await state.get_data()
    full_name   = d["full_name"]
    tg_username = d.get("tg_username", "")

    # ذخیره یا آپدیت کاربر
    user = await session.get(User, msg.from_user.id)
    if not user:
        user = User(id=msg.from_user.id)
        session.add(user)
    user.full_name   = full_name
    user.phone       = phone
    user.username    = tg_username
    user.registered  = True
    await session.commit()
    await state.clear()

    is_admin = msg.from_user.id in config.ADMIN_IDS
    await msg.answer(
        f"🎉 <b>ثبت‌نام با موفقیت انجام شد!</b>\n\n"
        f"👤 نام: <b>{full_name}</b>\n"
        f"📞 شماره: <b>{phone}</b>\n"
        f"📱 تلگرام: <code>@{tg_username}</code>\n\n"
        f"از منوی زیر استفاده کنید 👇",
        reply_markup=main_menu(is_admin=is_admin,
                               booking=config.BOOKING_ENABLED,
                               services=config.SERVICES_VISIBLE),
        parse_mode="HTML"
    )

# ── nav:main callback ─────────────────────────────────────────────────────────
@router.callback_query(F.data == "nav:main")
async def nav_main(cb, session: AsyncSession):
    user = await session.get(User, cb.from_user.id)
    is_admin = cb.from_user.id in config.ADMIN_IDS
    await cb.message.delete()
    await cb.bot.send_message(
        cb.from_user.id,
        "🏠 منوی اصلی",
        reply_markup=main_menu(is_admin=is_admin,
                               booking=config.BOOKING_ENABLED,
                               services=config.SERVICES_VISIBLE)
    )
    await cb.answer()

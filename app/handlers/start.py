from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User
from app.keyboards.menus import main_menu
from app.config import config

router = Router()

class RegFSM(StatesGroup):
    phone     = State()   # مرحله ۱: شماره تماس
    full_name = State()   # مرحله ۲: نام و نام خانوادگی

@router.message(CommandStart())
async def cmd_start(msg: Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    user = await session.get(User, msg.from_user.id)
    if user and user.registered:
        is_admin = msg.from_user.id in config.ADMIN_IDS
        await msg.answer(
            f"👋 خوش اومدی <b>{user.full_name}</b>!",
            reply_markup=main_menu(
                is_admin=is_admin,
                booking=config.BOOKING_ENABLED,
                services=config.SERVICES_VISIBLE
            ),
            parse_mode="HTML"
        )
        return

    tg_username = msg.from_user.username or str(msg.from_user.id)
    await state.update_data(tg_username=tg_username, tg_id=msg.from_user.id)

    # مرحله ۱: درخواست شماره تماس
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 اشتراک‌گذاری شماره", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await msg.answer(
        f"👋 سلام!\n\n"
        f"📱 شماره تلگرام: <code>@{tg_username}</code>\n\n"
        f"<b>مرحله ۱ از ۲</b>\n"
        f"شماره تماس خود را وارد کنید یا از دکمه زیر استفاده کنید:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.set_state(RegFSM.phone)

# ── مرحله ۱: دریافت شماره (contact یا متن) ───────────────────────────────────
@router.message(RegFSM.phone, F.contact)
async def reg_phone_contact(msg: Message, state: FSMContext):
    phone = msg.contact.phone_number
    if not phone.startswith("+"): phone = "+" + phone
    await state.update_data(phone=phone)
    await _ask_full_name(msg, state)

@router.message(RegFSM.phone, F.text)
async def reg_phone_text(msg: Message, state: FSMContext):
    phone = msg.text.strip().replace(" ", "")
    if not (phone.startswith("09") or phone.startswith("+98")) or len(phone) < 10:
        await msg.answer("❌ شماره معتبر نیست.\nمثال: <code>09123456789</code>", parse_mode="HTML")
        return
    await state.update_data(phone=phone)
    await _ask_full_name(msg, state)

async def _ask_full_name(msg: Message, state: FSMContext):
    await state.set_state(RegFSM.full_name)
    await msg.answer(
        f"✅ شماره ثبت شد.\n\n"
        f"<b>مرحله ۲ از ۲</b>\n"
        f"نام و نام خانوادگی خود را وارد کنید:\n"
        f"<i>(مثال: علی رضایی)</i>",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )

# ── مرحله ۲: دریافت نام و نام خانوادگی ──────────────────────────────────────
@router.message(RegFSM.full_name)
async def reg_full_name(msg: Message, state: FSMContext, session: AsyncSession):
    name = msg.text.strip()
    if len(name) < 3:
        await msg.answer("❌ نام باید حداقل ۳ حرف باشد. دوباره وارد کنید:")
        return

    d = await state.get_data()
    tg_username = d.get("tg_username", "")
    phone       = d.get("phone", "")

    user = await session.get(User, msg.from_user.id)
    if not user:
        user = User(id=msg.from_user.id)
        session.add(user)
    user.full_name  = name
    user.phone      = phone
    user.username   = tg_username
    user.registered = True
    await session.commit()
    await state.clear()

    is_admin = msg.from_user.id in config.ADMIN_IDS
    await msg.answer(
        f"🎉 <b>ثبت‌نام با موفقیت انجام شد!</b>\n\n"
        f"📱 تلگرام: <code>@{tg_username}</code>\n"
        f"📞 شماره: <b>{phone}</b>\n"
        f"👤 نام: <b>{name}</b>\n\n"
        f"از منوی زیر استفاده کنید 👇",
        reply_markup=main_menu(
            is_admin=is_admin,
            booking=config.BOOKING_ENABLED,
            services=config.SERVICES_VISIBLE
        ),
        parse_mode="HTML"
    )

# ── nav:main callback ─────────────────────────────────────────────────────────
@router.callback_query(F.data == "nav:main")
async def nav_main(cb: CallbackQuery, session: AsyncSession):
    is_admin = cb.from_user.id in config.ADMIN_IDS
    await cb.message.delete()
    await cb.bot.send_message(
        cb.from_user.id,
        "🏠 منوی اصلی",
        reply_markup=main_menu(
            is_admin=is_admin,
            booking=config.BOOKING_ENABLED,
            services=config.SERVICES_VISIBLE
        )
    )
    await cb.answer()

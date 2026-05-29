from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User
from app.keyboards.menus import main_menu, back_btn
from app.config import config

router = Router()

async def _get_or_create_user(session: AsyncSession, msg: Message) -> User:
    u = await session.get(User, msg.from_user.id)
    if not u:
        u = User(
            id=msg.from_user.id,
            full_name=msg.from_user.full_name,
            username=msg.from_user.username,
        )
        session.add(u)
        await session.commit()
    return u

@router.message(CommandStart())
async def cmd_start(msg: Message, session: AsyncSession):
    await _get_or_create_user(session, msg)
    is_admin = msg.from_user.id in config.ADMIN_IDS
    text = (
        f"✂️ به ربات <b>{config.SHOP_NAME}</b> خوش آمدید!\n\n"
        f"از منوی زیر گزینه مورد نظر را انتخاب کنید."
    )
    await msg.answer(text, reply_markup=main_menu(
        is_admin=is_admin,
        booking=config.BOOKING_ENABLED,
        services=config.SERVICES_VISIBLE,
        payment=config.PAYMENT_ENABLED,
    ), parse_mode="HTML")

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
        ), parse_mode="HTML"
    )
    await cb.answer()

@router.message(F.text == "📞 اطلاعات آرایشگاه")
async def shop_info(msg: Message):
    text = (
        f"🏪 <b>{config.SHOP_NAME}</b>\n"
        f"📍 {config.SHOP_ADDRESS or '—'}\n"
        f"📞 {config.SHOP_PHONE or '—'}"
    )
    await msg.answer(text, reply_markup=back_btn("nav:main"), parse_mode="HTML")

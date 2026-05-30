from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Service
from app.keyboards.menus import back_btn
from app.config import config

router = Router()

@router.message(F.text == "✂️ خدمات و قیمت‌ها")
async def show_services(msg: Message, session: AsyncSession):
    if not config.SERVICES_VISIBLE:
        await msg.answer("⚠️ لیست خدمات در حال حاضر در دسترس نیست."); return
    r = await session.execute(select(Service).where(Service.is_active == True).order_by(Service.id))
    services = r.scalars().all()
    if not services:
        await msg.answer("⚠️ هیچ خدماتی تعریف نشده است."); return
    lines = [f"✂️ <b>{config.SHOP_NAME}</b> — لیست خدمات\n"]
    for s in services:
        lines.append(f"• <b>{s.name}</b>\n  💰 {s.price:,} تومان  |  ⏱ {s.duration} دقیقه")
    await msg.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text == "📞 اطلاعات آرایشگاه")
async def show_shop_info(msg: Message):
    name    = config.SHOP_NAME    or "—"
    phone   = config.SHOP_PHONE   or "—"
    address = config.SHOP_ADDRESS or "—"
    card    = config.CARD_NUMBER  or "—"
    holder  = config.CARD_HOLDER  or "—"

    text = (
        f"🏪 <b>{name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📞 تلفن: <b>{phone}</b>\n"
        f"📍 آدرس: <b>{address}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 شماره کارت:\n"
        f"<code>{card}</code>\n"
        f"👤 به نام: <b>{holder}</b>"
    )
    await msg.answer(text, parse_mode="HTML")

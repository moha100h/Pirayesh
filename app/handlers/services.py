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

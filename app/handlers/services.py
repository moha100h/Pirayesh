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
        await msg.answer("⚠️ نمایش خدمات در حال حاضر غیرفعال است.")
        return
    r = await session.execute(select(Service).where(Service.is_active == True))
    services = r.scalars().all()
    if not services:
        await msg.answer("هنوز خدماتی ثبت نشده.", reply_markup=back_btn())
        return
    lines = ["✂️ <b>خدمات و قیمت‌ها</b>\n"]
    for s in services:
        lines.append(f"• <b>{s.name}</b> — {s.price:,} تومان  ({s.duration} دقیقه)")
    await msg.answer("\n".join(lines), reply_markup=back_btn(), parse_mode="HTML")

import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from aiogram import Bot
from app.db.models import Booking, BookingStatus, TimeSlot, Service
from app.services.jalali import to_jalali_with_year, fmt_price
from app.config import config

logger = logging.getLogger(__name__)

REMINDER_INTERVAL = 60        # هر ۶۰ ثانیه چک می‌کنه
PENDING_THRESHOLD = 30 * 60   # ۳۰ دقیقه به ثانیه

async def check_pending_bookings(bot: Bot, session_factory: async_sessionmaker):
    """هر ۶۰ ثانیه رزروهای pending بیشتر از ۳۰ دقیقه رو به ادمین اطلاع می‌ده"""
    async with session_factory() as session:
        threshold_time = datetime.utcnow() - timedelta(seconds=PENDING_THRESHOLD)
        r = await session.execute(
            select(Booking).where(
                Booking.status == BookingStatus.PENDING,
                Booking.created_at <= threshold_time,
                Booking.notified_admin == False   # فقط یه بار اطلاع بده
            )
            .options(
                selectinload(Booking.user),
                selectinload(Booking.service),
                selectinload(Booking.slot)
            )
        )
        bookings = r.scalars().all()
        if not bookings:
            return

        count = len(bookings)
        lines = [f"⏰ <b>{count} نوبت در انتظار تایید (بیش از ۳۰ دقیقه)</b>\n"]
        for b in bookings:
            name = b.user.full_name if b.user else "—"
            svc  = b.service.name if b.service else "—"
            date = to_jalali_with_year(b.slot.date) if b.slot else "—"
            t    = b.slot.time if b.slot else "—"
            lines.append(f"• #{b.id} — {name} | {svc} | {date} {t}")
            b.notified_admin = True

        await session.commit()

        text = "\n".join(lines) + "\n\n👆 برای بررسی وارد پنل مدیریت شوید."
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Cannot notify admin {admin_id}: {e}")

async def start_scheduler(bot: Bot, session_factory: async_sessionmaker):
    logger.info("Scheduler started — checking pending bookings every 60s")
    while True:
        try:
            await check_pending_bookings(bot, session_factory)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(REMINDER_INTERVAL)

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.models import Base
from app.handlers import start, booking, payment, services, admin
from app.middleware.db import DbSessionMiddleware
from app.config import config
from app.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)

async def main():
    engine = create_async_engine(config.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    bot = Bot(token=config.BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware(session_factory))

    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(booking.router)
    dp.include_router(payment.router)
    dp.include_router(services.router)

    # یادآوری ۳۰ دقیقه‌ای به ادمین
    asyncio.create_task(start_scheduler(bot, session_factory))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

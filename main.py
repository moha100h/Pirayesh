import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.db.database import init_db, AsyncSessionLocal
from app.handlers import start, booking, services, admin, payment

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # middleware: inject session
    from aiogram import BaseMiddleware
    from typing import Callable, Awaitable, Any
    from aiogram.types import TelegramObject

    class DbMiddleware(BaseMiddleware):
        async def __call__(self, handler: Callable, event: TelegramObject, data: dict) -> Any:
            async with AsyncSessionLocal() as session:
                data["session"] = session
                return await handler(event, data)

    dp.message.middleware(DbMiddleware())
    dp.callback_query.middleware(DbMiddleware())

    dp.include_router(start.router)
    dp.include_router(booking.router)
    dp.include_router(services.router)
    dp.include_router(payment.router)
    dp.include_router(admin.router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

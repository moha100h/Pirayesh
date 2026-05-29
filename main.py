import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import TelegramObject
from aiogram import BaseMiddleware
from typing import Callable, Awaitable, Any

from app.config import config
from app.db.database import init_db, AsyncSessionLocal
from app.handlers import start, booking, services, admin, payment

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

class DbMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event: TelegramObject, data: dict) -> Any:
        async with AsyncSessionLocal() as session:
            data["session"] = session
            return await handler(event, data)

async def main():
    await init_db()
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(DbMiddleware())
    dp.callback_query.middleware(DbMiddleware())

    dp.include_router(start.router)
    dp.include_router(booking.router)
    dp.include_router(services.router)
    dp.include_router(payment.router)
    dp.include_router(admin.router)

    logging.info(f"Bot started | Shop: {config.SHOP_NAME} | Admins: {config.ADMIN_IDS}")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())

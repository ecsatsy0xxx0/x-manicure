# bot.py
import asyncio
import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from config import settings
from database.db import init_db
from handlers import common, subscription, user_booking, user_misc, admin
from scheduler import scheduler, restore_jobs

load_dotenv()


async def main():
    init_db()

    proxy_url = os.getenv("PROXY_URL") 
    session = None
    if proxy_url:
        session = AiohttpSession(proxy=proxy_url)

    bot = Bot(
        token=settings.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common.router)
    dp.include_router(subscription.router)
    dp.include_router(user_booking.router)
    dp.include_router(user_misc.router)
    dp.include_router(admin.router)

    scheduler.start()
    await restore_jobs(bot)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
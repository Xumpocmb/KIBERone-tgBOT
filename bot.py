import asyncio
import os
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from loguru import logger
from pytz import timezone

from crm_logic.alfa_crm_api import check_client_balance_from_crm
from database.engine import create_db, session_maker
from tg_bot.handlers import handler_start
from tg_bot.handlers import handler_main_menu
from tg_bot.handlers.inline_handlers import inline_handler_tg_links
from tg_bot.middlewares.middleware_antiflood import AntiFloodMiddleware
from tg_bot.middlewares.middleware_chat_action import ChatActionMiddleware
from tg_bot.middlewares.middleware_database import DataBaseSession

logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")

load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DEBUG = os.environ.get('DEBUG') == 'True'


async def on_startup(bot: Bot):
    logger.info('Starting bot..')
    logger.info('Creating DB..')
    await create_db()
    logger.info('DB created. Bot started.')


async def on_shutdown(bot: Bot):
    logger.info('Processing shutdown..')


async def main():
    bot: Bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp: Dispatcher = Dispatcher(storage=MemoryStorage())

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.message.middleware(DataBaseSession(session_pool=session_maker))
    dp.message.middleware(AntiFloodMiddleware())
    dp.message.middleware(ChatActionMiddleware())

    dp.include_routers(
        handler_start.start_router,
        handler_main_menu.main_menu_router,
        inline_handler_tg_links.inline_tg_links_router,
    )

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")

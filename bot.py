import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from tg_bot.database.engine import create_db, session_maker
from tg_bot.handlers import handler_main_menu
from tg_bot.handlers import handler_start
from tg_bot.handlers.admin_handlers import (
    admin_handler_user_list,
    admin_handler_send_all,
    admin_handler_check_tasks,
    admin_handler_parthner_statistic,
    admin_handler_send_to_debtors,
)
from tg_bot.handlers.inline_handlers import inline_handler_all_links
from tg_bot.handlers.inline_handlers import (
    inline_handler_tg_links,
    inline_handler_main,
    inline_handler_faq,
    inline_handler_clients_bonuses,
    inline_handler_partner,
    inline_handler_contact,
    inline_handler_english_platform,
    inline_handler_erip,
    inline_handler_user_scheduler,
    inline_handler_trial_lesson,
    inline_handler_crm_balance,
)
from tg_bot.middlewares.middleware_chat_action import ChatActionMiddleware
from tg_bot.middlewares.middleware_database import DataBaseSession
from tg_bot.scheduler_config import setup_scheduler, stop_scheduler
from tg_bot.utils.set_commands import set_main_menu

from logger_config import get_logger

logger = get_logger()

load_dotenv()
DEBUG = os.environ.get("BOT_DEBUG")
if DEBUG == "dev":
    BOT_TOKEN = os.environ.get("BOT_TOKEN2")
else:
    BOT_TOKEN = os.environ.get("BOT_TOKEN")


async def on_startup(bot: Bot):
    logger.info("Starting bot..")
    logger.info("Creating DB..")
    await create_db()
    setup_scheduler()
    logger.info("DB created. Bot started.")


async def on_shutdown(bot: Bot):
    logger.info("Processing shutdown..")
    stop_scheduler()


async def main():
    bot: Bot = Bot(
        token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp: Dispatcher = Dispatcher(storage=MemoryStorage())

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.message.middleware(DataBaseSession(session_pool=session_maker))
    # dp.message.middleware(AntiFloodMiddleware())
    dp.message.middleware(ChatActionMiddleware())

    dp.include_routers(
        handler_start.start_router,
        inline_handler_tg_links.inline_tg_links_router,
        inline_handler_all_links.button_link_router,
        inline_handler_faq.faq_router,
        inline_handler_clients_bonuses.promo_router,
        inline_handler_partner.partner_router,
        inline_handler_contact.manager_contact_router,
        inline_handler_english_platform.english_platform_router,
        inline_handler_erip.erip_router,
        inline_handler_user_scheduler.user_scheduler_router,
        inline_handler_trial_lesson.trial_lesson_router,
        inline_handler_crm_balance.crm_balance_router,
        handler_main_menu.main_menu_router,
        # admin
        admin_handler_user_list.admin_user_list_router,
        admin_handler_send_all.admin_send_all_router,
        admin_handler_check_tasks.admin_tasks_list_router,
        admin_handler_parthner_statistic.admin_handler_parthner_statistic_router,
        admin_handler_send_to_debtors.admin_send_to_debtors,
        # last router
        inline_handler_main.inline_main_router,
    )

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await set_main_menu(bot)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), timeout_seconds=30, polling_timeout=30)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")

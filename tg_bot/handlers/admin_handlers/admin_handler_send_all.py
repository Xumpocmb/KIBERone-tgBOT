from aiogram import Router, F
from loguru import logger

from database.engine import session_maker
from tg_bot.middlewares.middleware_database import DataBaseSession

logger.add(
    "debug.log",
    format="{time} {level} {message}",
    level="ERROR",
    rotation="1 MB",
    compression="zip",
)

admin_send_all_router: Router = Router()
admin_send_all_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


@admin_send_all_router.callback_query(F.data == "admin_send_all")
async def send_all_handler():
    pass
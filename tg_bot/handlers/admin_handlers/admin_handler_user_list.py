from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import session_maker
from database.orm_query import get_all_users
from tg_bot.middlewares.middleware_database import DataBaseSession

logger.add(
    "debug.log",
    format="{time} {level} {message}",
    level="ERROR",
    rotation="1 MB",
    compression="zip",
)

admin_user_list_router: Router = Router()
admin_user_list_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


@admin_user_list_router.callback_query(F.data == "admin_user_list")
async def user_list_handler(callback: CallbackQuery, session: AsyncSession):
    users_in_db = await get_all_users(session)
    user_info = "\n".join(
        f"ID:{user.id}: {user.first_name, user.last_name if user.last_name else user.username}, Phone: {user.phone_number}, Created At: {user.created_at}\n"
        for user in users_in_db)
    await callback.message.answer(text=f"Список пользователей:\n\n{user_info}")
    await callback.answer()
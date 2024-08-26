import asyncio

from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import session_maker
from database.orm_query import get_all_users
from tg_bot.middlewares.middleware_database import DataBaseSession


admin_user_list_router: Router = Router()
admin_user_list_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


@admin_user_list_router.callback_query(F.data == "admin_user_list")
async def user_list_handler(callback: CallbackQuery, session: AsyncSession):
    users_in_db = await get_all_users(session)
    batch_size = 10
    for i in range(0, len(users_in_db), batch_size):
        batch = users_in_db[i:i + batch_size]


        user_info = "\n".join(
            f"ID:{user.id}: {user.first_name, user.last_name if user.last_name else user.username}, "
            f"Phone: {user.phone_number}, Created At: {user.created_at}"
            for user in batch
        )


        await callback.message.answer(text=f"Пользователи:\n\n{user_info}")
        await asyncio.sleep(1)

    await callback.answer()

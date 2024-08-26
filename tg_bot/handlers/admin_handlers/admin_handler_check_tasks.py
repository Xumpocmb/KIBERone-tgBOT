from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import session_maker
from database.orm_query import get_all_users, get_tasks
from tg_bot.middlewares.middleware_database import DataBaseSession


admin_tasks_list_router: Router = Router()
admin_tasks_list_router.callback_query.middleware(
    DataBaseSession(session_pool=session_maker)
)


@admin_tasks_list_router.callback_query(F.data == "tasks_list")
async def tasks_list_handler(callback: CallbackQuery, session: AsyncSession):
    tasks_in_db = await get_tasks(session)
    tasks_info = "\n".join(
        f"ID:{task.id}\n"
        for task in tasks_in_db
    )
    await callback.message.answer(text=f"Список пользователей:\n\n{tasks_info}")
    await callback.answer()

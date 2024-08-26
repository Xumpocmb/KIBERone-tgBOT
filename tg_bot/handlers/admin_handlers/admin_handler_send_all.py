import asyncio

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import session_maker
from database.orm_query import get_all_users
from tg_bot.middlewares.middleware_database import DataBaseSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State


class BroadcastStates(StatesGroup):
    waiting_for_text = State()


admin_send_all_router: Router = Router()
admin_send_all_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


@admin_send_all_router.callback_query(F.data == "admin_send_all")
async def send_all_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.message.answer("Пожалуйста, введите текст для рассылки\n"
                                  "Для отмены введите 'отмена' (без ковычек):")
    await state.set_state(BroadcastStates.waiting_for_text)
    await callback.answer()


@admin_send_all_router.message(BroadcastStates.waiting_for_text)
async def get_broadcast_text(message: Message, state: FSMContext, session: AsyncSession):
    broadcast_text = message.text

    if broadcast_text == "отмена":
        await message.answer("Рассылка отменена.")
        await state.clear()
    else:
        users = await get_all_users(session)
        await message.answer("Рассылка запущена.")
        for user in users:
            try:
                await message.bot.send_message(user.tg_id, broadcast_text)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение пользователю {user.tg_id}: {e}")
        await message.answer("Рассылка завершена.")
        await state.clear()
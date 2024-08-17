from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import session_maker
from tg_bot.filters.filter_admin import check_admin
from tg_bot.handlers.handler_main_menu import get_user_keyboard
from tg_bot.middlewares.middleware_database import DataBaseSession

inline_main_router: Router = Router()
inline_main_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


# присылает главное inline меню
@inline_main_router.callback_query(F.data == 'inline_main')
async def process_button_inline_back_to_main(callback: CallbackQuery, session: AsyncSession):
    is_admin = check_admin(callback.from_user.id)
    if is_admin:
        pass
    else:
        await callback.message.answer(text='Выберите действие..',
                                      reply_markup=await get_user_keyboard(session, callback.from_user.id))
        await callback.message.delete()
        await callback.answer()


# отвечает на любой call-back для теста
@inline_main_router.callback_query()
async def process_any_button_(callback: CallbackQuery):
    logger.info(f'Callback: {callback.data}')
    await callback.message.delete()
    await callback.answer()

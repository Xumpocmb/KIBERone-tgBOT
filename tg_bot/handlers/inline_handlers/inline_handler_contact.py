from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import session_maker
from tg_bot.middlewares.middleware_database import DataBaseSession

manager_contact_router: Router = Router()
manager_contact_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


@manager_contact_router.callback_query(F.data == 'contact')
async def process_button_faq_press(callback: CallbackQuery, session: AsyncSession):
    await callback.message.answer(text='Контакт менеджера:')  # reply_markup=make_inline_contact_city_kb()
    await callback.message.delete()
    await callback.answer()


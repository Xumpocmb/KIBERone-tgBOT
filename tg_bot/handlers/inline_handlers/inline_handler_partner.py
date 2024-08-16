from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.operators import eq

from database.engine import session_maker
from database.models import Partner
from tg_bot.keyboards.inline_keyboards.inline_keyboard_partner import make_inline_partner_kb
from tg_bot.middlewares.middleware_database import DataBaseSession

partner_router: Router = Router()
partner_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))

# главное меню раздела Partner
@partner_router.callback_query(F.data == 'partner')
async def process_button_partner_press(callback: CallbackQuery, session: AsyncSession):
    await callback.message.answer(text='Наши партнеры:',
                                  reply_markup=await make_inline_partner_kb(session))
    await callback.message.delete()
    await callback.answer()


# пункт раздела наши партнеры
@partner_router.callback_query(F.data.startswith('partner-'))
async def process_button_partner_question_press(callback: CallbackQuery, session: AsyncSession):
    query = select(Partner).where(eq(Partner.id, int(callback.data.split('-')[1])))
    result = await session.execute(query)
    partner = result.scalar()
    await callback.message.answer(text=partner.description,
                                  reply_markup=await make_inline_partner_kb(session))
    await callback.message.delete()
    await callback.answer()

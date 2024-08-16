from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.operators import eq

from database.engine import session_maker
from database.models import Promotion
from tg_bot.keyboards.inline_keyboards.inline_keyboard_promo import make_inline_promo_kb
from tg_bot.middlewares.middleware_database import DataBaseSession

promo_router: Router = Router()
promo_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


# главное меню раздела Promo
@promo_router.callback_query(F.data == 'promo')
async def process_button_promo_press(callback: CallbackQuery, session: AsyncSession):
    await callback.message.answer(text='Наши акции:',
                                  reply_markup=await make_inline_promo_kb(session))
    await callback.message.delete()
    await callback.answer()


# пункт раздела наши акции
@promo_router.callback_query(F.data.startswith('promo-'))
async def process_button_promo_question_press(callback: CallbackQuery, session: AsyncSession):
    query = select(Promotion).where(eq(Promotion.id, int(callback.data.split('-')[1])))
    result = await session.execute(query)
    promo = result.scalar()
    await callback.message.answer(text=promo.answer,
                                  reply_markup=await make_inline_promo_kb(session))
    await callback.message.delete()
    await callback.answer()



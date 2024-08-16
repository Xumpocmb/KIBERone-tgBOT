from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery, FSInputFile
from sqlalchemy.sql.operators import eq

# from database.engine import session_maker
from database.models import FAQ
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.engine import session_maker
from tg_bot.keyboards.inline_keyboards.inline_keyboard_faq import make_inline_faq_kb
from tg_bot.middlewares.middleware_database import DataBaseSession

faq_router: Router = Router()
faq_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


# главное меню раздела FAQ
@faq_router.callback_query(F.data == 'FAQ')
async def process_button_faq_press(callback: CallbackQuery, session: AsyncSession):
    await callback.message.answer(text='Часто задаваемые вопросы:', reply_markup = await make_inline_faq_kb(session))
    await callback.message.delete()
    await callback.answer()


# пункт раздела FAQ
@faq_router.callback_query(F.data.startswith('faq-'))
async def process_button_faq_question_press(callback: CallbackQuery, session: AsyncSession):
    query = select(FAQ).where(eq(FAQ.id, int(callback.data.split('-')[1])))
    result = await session.execute(query)
    faq = result.scalar()
    await callback.message.answer(text=faq.answer, reply_markup=await make_inline_faq_kb(session))
    if callback.data == 'faq-2':
        document1 = FSInputFile(path='files/Программа (младшая группа) А3.pdf', filename='Программа обучения младшая группа.pdf')
        document2 = FSInputFile(path='files/Программа (средняя группа) А3.pdf', filename='Программа обучения средняя группа.pdf')
        document3 = FSInputFile(path='files/Программа (старшая группа) А3.pdf', filename='Программа обучения старшая группа.pdf')
        await callback.message.answer_document(document=document1, caption='Программа обучения младшая группа')
        await callback.message.answer_document(document=document2, caption='Программа обучения средняя группа')
        await callback.message.answer_document(document=document3, caption='Программа обучения старшая группа')
    await callback.message.delete()
    await callback.answer()



from aiogram import F
from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, FSInputFile
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.database.engine import session_maker
from tg_bot.database.models import FAQ
from logger_config import get_logger
from tg_bot.keyboards.inline_keyboards.inline_keyboard_faq import make_inline_faq_kb
from tg_bot.middlewares.middleware_database import DataBaseSession

logger = get_logger()

faq_router: Router = Router()
faq_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


@faq_router.callback_query(F.data == 'FAQ')
async def process_button_faq_press(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    logger.debug(f"Получен запрос на FAQ от пользователя с ID: {user_id}")

    try:
        faq_kb = await make_inline_faq_kb(session)
        logger.debug(f"Клавиатура FAQ для пользователя с ID {user_id} успешно получена.")

        await callback.message.answer(
            text='Часто задаваемые вопросы:',
            reply_markup=faq_kb
        )
        logger.info(f"Пользователю с ID {user_id} отправлено сообщение с FAQ.")

        await callback.answer()
        logger.debug(f"Обработка запроса FAQ завершена для пользователя с ID {user_id}.")
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса FAQ от пользователя с ID {user_id}: {e}")


# пункт раздела FAQ
@faq_router.callback_query(F.data.startswith('faq-'))
async def process_faq_question(callback: CallbackQuery, session: AsyncSession):
    """Process a callback query to show a single FAQ question and answer."""
    try:
        faq_id = int(callback.data.split('-')[1])
        query = select(FAQ).where(FAQ.id == faq_id)
        faq = (await session.execute(query)).scalars().first()
        if faq is None:
            await callback.message.answer(
                text="Вопрос FAQ не найден.",
                reply_markup=await make_inline_faq_kb(session)
            )
        else:
            await callback.message.answer(
                text=faq.answer,
                reply_markup=await make_inline_faq_kb(session)
            )
            if callback.data == 'faq-2':
                for file in (
                    ('files/Программа (младшая группа) А3.pdf', 'Программа обучения младшая группа.pdf'),
                    ('files/Программа (средняя группа) А3.pdf', 'Программа обучения средняя группа.pdf'),
                    ('files/Программа (старшая группа) А3.pdf', 'Программа обучения старшая группа.pdf'),
                ):
                    await callback.message.answer_document(document=FSInputFile(path=file[0], filename=file[1]))
    except (TelegramAPIError, SQLAlchemyError) as e:
        logger.error(f"An error occurred while processing the FAQ callback query: {e}")
    finally:
        await callback.answer()

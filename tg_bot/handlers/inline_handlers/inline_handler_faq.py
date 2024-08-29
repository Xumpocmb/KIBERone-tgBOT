from aiogram import F
from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, FSInputFile
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import session_maker
from database.models import FAQ
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

        await callback.message.delete()
        logger.debug(f"Исходное сообщение удалено для пользователя с ID {user_id}.")

        await callback.answer()
        logger.debug(f"Обработка запроса FAQ завершена для пользователя с ID {user_id}.")
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса FAQ от пользователя с ID {user_id}: {e}")


# пункт раздела FAQ
@faq_router.callback_query(F.data.startswith('faq-'))
async def process_button_faq_question_press(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    logger.debug(f"Получен запрос на FAQ от пользователя с ID: {user_id}, данные: {callback.data}")

    try:
        faq_id = int(callback.data.split('-')[1])
        logger.debug(f"Извлечен ID вопроса: {faq_id}")

        query = select(FAQ).where(FAQ.id == faq_id)
        result = await session.execute(query)
        faq = result.scalar()
        logger.debug(f"Получен ответ FAQ для ID {faq_id}: {faq.answer}")

        await callback.message.answer(
            text=faq.answer,
            reply_markup=await make_inline_faq_kb(session)
        )
        logger.info(f"Отправлен ответ на FAQ пользователю с ID {user_id}.")

        if callback.data == 'faq-2':
            document1 = FSInputFile(path='files/Программа (младшая группа) А3.pdf',
                                    filename='Программа обучения младшая группа.pdf')
            document2 = FSInputFile(path='files/Программа (средняя группа) А3.pdf',
                                    filename='Программа обучения средняя группа.pdf')
            document3 = FSInputFile(path='files/Программа (старшая группа) А3.pdf',
                                    filename='Программа обучения старшая группа.pdf')

            await callback.message.answer_document(document=document1, caption='Программа обучения младшая группа')
            logger.debug(f"Документ 'Программа обучения младшая группа' отправлен пользователю с ID {user_id}.")

            await callback.message.answer_document(document=document2, caption='Программа обучения средняя группа')
            logger.debug(f"Документ 'Программа обучения средняя группа' отправлен пользователю с ID {user_id}.")

            await callback.message.answer_document(document=document3, caption='Программа обучения старшая группа')
            logger.debug(f"Документ 'Программа обучения старшая группа' отправлен пользователю с ID {user_id}.")

        await callback.message.delete()
        logger.debug(f"Исходное сообщение удалено для пользователя с ID {user_id}.")

        await callback.answer()
        logger.debug(f"Обработка запроса FAQ завершена для пользователя с ID {user_id}.")
    except TelegramAPIError as e:
        logger.error(f"Ошибка API Telegram при обработке запроса FAQ от пользователя с ID {user_id}: {e}")
    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при выполнении запроса FAQ для пользователя с ID {user_id}: {e}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при обработке запроса FAQ от пользователя с ID {user_id}: {e}")

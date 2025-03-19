from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.database.models import Promotion

from logger_config import get_logger

logger = get_logger()



async def make_inline_promo_kb(session: AsyncSession) -> InlineKeyboardMarkup:
    logger.debug("Начало создания клавиатуры акций.")
    buttons = []

    try:
        query = select(Promotion)
        results = await session.scalars(query)
        logger.debug("Запрос к базе данных выполнен успешно.")

        for item in results:
            logger.debug(f"Обработка элемента с ID {item.id} и вопросом: {item.question}")
            buttons.append(
                InlineKeyboardButton(text=item.question, callback_data=f'promo-{item.id}')
            )

        buttons.append(InlineKeyboardButton(text='<< Назад', callback_data='inline_main'))
        logger.debug("Кнопка 'Назад' добавлена.")

        buttons = [[button] for button in buttons]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons, resize_keyboard=True,
                                        input_field_placeholder="Выберите действие..")
        logger.debug("Клавиатура создана успешно.")
        return keyboard

    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при создании клавиатуры акций: {e}")

    except Exception as e:
        logger.error(f"Неизвестная ошибка при создании клавиатуры акций: {e}")


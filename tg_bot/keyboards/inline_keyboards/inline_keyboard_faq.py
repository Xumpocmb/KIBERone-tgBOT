from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FAQ

from loguru import logger
logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")


async def make_inline_faq_kb(session: AsyncSession) -> InlineKeyboardMarkup:
    try:
        buttons = []
        query = select(FAQ)
        results = await session.scalars(query)
        for item in results:
            buttons.append(InlineKeyboardButton(text=item.question, callback_data=f'faq-{str(item.id)}'))

        buttons.append(InlineKeyboardButton(text='<< Назад', callback_data='inline_main'))

        buttons = [[button] for button in buttons]
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=buttons,
            resize_keyboard=True,
            input_field_placeholder="Выберите действие.."
        )

        logger.debug("Создана клавиатура для FAQ")
        return keyboard

    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры FAQ: {e}")


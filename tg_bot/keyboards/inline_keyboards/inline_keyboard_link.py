from sqlalchemy import select

from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from sqlalchemy.dialects.postgresql.psycopg2 import logger

from database.engine import session_maker
from database.models import Link


async def make_inline_link_kb() -> InlineKeyboardMarkup:
    buttons = []
    async with session_maker() as session:
        query = select(Link)
        results = await session.execute(query)
        logger.debug(results)
        for item in results.scalars():
            buttons.append(InlineKeyboardButton(text=str(item.link_name), url=str(item.link_url)))
    buttons.append(InlineKeyboardButton(text='<< Назад', callback_data='inline_main'))
    buttons = [[button] for button in buttons]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons, resize_keyboard=True,
                                    input_field_placeholder="Выберите действие..")
    return keyboard



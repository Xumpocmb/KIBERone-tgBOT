from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FAQ


async def make_inline_faq_kb(session: AsyncSession) -> InlineKeyboardMarkup:
    buttons = []
    query = select(FAQ)
    results = await session.scalars(query)
    for item in results:
        buttons.append(InlineKeyboardButton(text=item.question, callback_data=f'faq-{str(item.id)}'))
    buttons.append(InlineKeyboardButton(text='<< Назад', callback_data='inline_main'))
    buttons = [[button] for button in buttons]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons, resize_keyboard=True,
                                    input_field_placeholder="Выберите действие..")
    return keyboard



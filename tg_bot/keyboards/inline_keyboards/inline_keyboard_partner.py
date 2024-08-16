from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Partner


async def make_inline_partner_kb(session: AsyncSession) -> InlineKeyboardMarkup:
    buttons = []
    query = select(Partner)
    results = await session.scalars(query)
    for item in results:
        buttons.append(InlineKeyboardButton(text=item.partner, callback_data=f'partner-{str(item.id)}'))
    buttons.append(InlineKeyboardButton(text='<< Назад', callback_data='inline_main'))
    buttons = [[button] for button in buttons]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons, resize_keyboard=True,
                                    input_field_placeholder="Выберите действие..")
    return keyboard



from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.database.models import Partner

from logger_config import get_logger

logger = get_logger()



async def make_inline_partner_kb(session: AsyncSession) -> InlineKeyboardMarkup:
    buttons = []

    try:
        query = select(Partner)
        result = await session.execute(query)
        partners = result.scalars().all()

        for item in partners:
            buttons.append(InlineKeyboardButton(text=item.partner, callback_data=f'partner-{item.id}'))

        buttons.append(InlineKeyboardButton(text='<< Назад', callback_data='inline_main'))
        buttons = [[button] for button in buttons]
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=buttons,
            resize_keyboard=True,
            input_field_placeholder="Выберите действие.."
        )

        logger.debug("Создана клавиатура партнеров")
        return keyboard

    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры партнеров: {e}")
        # Возвращаем пустую клавиатуру или клавиатуру с сообщением об ошибке
        return InlineKeyboardMarkup()



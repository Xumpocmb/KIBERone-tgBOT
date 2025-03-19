from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from tg_bot.database.engine import session_maker
from tg_bot.database.models import Link

from logger_config import get_logger

logger = get_logger()


async def make_inline_link_kb() -> InlineKeyboardMarkup:
    buttons = []

    try:
        async with session_maker() as session:
            query = select(Link)
            result = await session.execute(query)
            links = result.scalars().all()

            for item in links:
                buttons.append(InlineKeyboardButton(text=str(item.link_name), url=str(item.link_url)))

        buttons.append(InlineKeyboardButton(text='<< Назад', callback_data='inline_main'))
        buttons = [[button] for button in buttons]
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=buttons,
            resize_keyboard=True,
            input_field_placeholder="Выберите действие.."
        )

        logger.debug("Создана клавиатура с ссылками")
        return keyboard

    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры с ссылками: {e}")



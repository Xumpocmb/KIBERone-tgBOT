from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.database.models import Partner, PartnerCategory

from logger_config import get_logger

logger = get_logger()


async def make_inline_partner_categories_kb(session: AsyncSession) -> InlineKeyboardMarkup:
    """Формирует список категорий партнеров"""
    buttons = []
    try:
        query = select(PartnerCategory)
        result = await session.execute(query)
        categories = result.scalars().all()


        for category in categories:
            buttons.append(InlineKeyboardButton(text=category.category, callback_data=f"partners_of_category-{str(category.id)}"))

        buttons.append(InlineKeyboardButton(text='<< Главное меню', callback_data='inline_main'))
        buttons = [[button] for button in buttons]
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=buttons,
            resize_keyboard=True,
            input_field_placeholder="Выберите категорию.."
        )
        return keyboard
    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры категорий партнеров: {e}")
        return InlineKeyboardMarkup()



async def make_inline_partner_kb(session: AsyncSession, category_id: int, is_study: int = 0) -> InlineKeyboardMarkup:
    """Формирует список партнеров определенной категории"""
    buttons = []

    try:
        query = select(Partner).where(Partner.category_id == category_id)
        result = await session.execute(query)
        partners = result.scalars().all()

        if is_study == 1:
            for item in partners:
                buttons.append(InlineKeyboardButton(text=item.partner, callback_data=f'partner-{item.id}'))
        else:
            for item in partners:
                buttons.append(InlineKeyboardButton(text=item.partner, callback_data='lets_study'))

        buttons.append(InlineKeyboardButton(text='<< Назад', callback_data='partners_categories'))
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
        return InlineKeyboardMarkup()




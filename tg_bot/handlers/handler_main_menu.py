from aiogram import Router, F
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from crm_logic.alfa_crm_api import find_user_by_phone
from database.orm_query import orm_get_user
from tg_bot.keyboards.inline_keyboards.inline_keyboard_main_menu import main_menu_inline_keyboard

logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")
main_menu_router: Router = Router()


@main_menu_router.message(F.text == 'Главное меню')
async def main_menu_handler(message: Message, session: AsyncSession):
    user_in_db = await orm_get_user(session, tg_id=message.from_user.id)
    logger.debug(user_in_db.phone_number)
    # user_in_crm = await find_user_by_phone(user_in_db.phone_number)
    """
    отправить запрос в црм. найти клиента.
    если лид с группой и стади 1 то полная клава
    если лид с группой стади 0 то убрать инглиш, партнеры как у лида, без промокодов
    если лид без группы и стади 0 то контакт жени. партнеры без промокода, ссылки на соцсети
    """
    logger.debug('Главное меню')
    await message.answer('Главное меню', reply_markup=main_menu_inline_keyboard)

from aiogram import Router, F
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.filters import Command
from crm_logic.alfa_crm_api import find_user_by_phone, get_client_lessons
from database.orm_query import orm_get_user
from tg_bot.keyboards.inline_keyboards.inline_keyboard_main_menu import main_menu_inline_keyboard_for_client, \
    main_menu_inline_keyboard_for_lead_with_group, main_menu_inline_keyboard_for_lead_without_group

logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")

main_menu_router: Router = Router()


@main_menu_router.message(Command("menu"))
async def main_menu_handler(message: Message, session: AsyncSession):
    logger.debug('Главное меню')
    await message.answer('Главное меню', reply_markup=await get_user_keyboard(session, message.from_user.id))


async def get_user_keyboard(session: AsyncSession, tg_id: int):
    user_in_db = await orm_get_user(session, tg_id)
    logger.debug(user_in_db.phone_number)
    user_in_crm_data = await find_user_by_phone(user_in_db.phone_number)
    user_crm_id = user_in_crm_data.get("items", [])[0].get("id", None)

    user_crm_branch_ids = user_in_crm_data.get("items", [])[0].get("branch_ids", None)
    lessons = await get_client_lessons(user_crm_id=user_crm_id, branch_ids=user_crm_branch_ids)

    user_crm_is_study = user_in_crm_data.get("items", [])[0].get("is_study", None)

    if user_crm_is_study:
        logger.debug("is_study 1")
        logger.debug('Главное меню')
        return main_menu_inline_keyboard_for_client
    elif lessons.get("total") > 0:
        return main_menu_inline_keyboard_for_lead_with_group
    else:
        logger.debug('Главное меню')
        return main_menu_inline_keyboard_for_lead_without_group

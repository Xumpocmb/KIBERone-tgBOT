from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.filters import Command
from tg_bot.database.orm_query import orm_get_user_by_tg_id
from tg_bot.filters.filter_admin import check_admin
from tg_bot.keyboards.inline_keyboards.inline_admin_main_menu import admin_main_menu_inline_keyboard
from tg_bot.keyboards.inline_keyboards.inline_keyboard_main_menu import main_menu_inline_keyboard_for_client, \
    main_menu_inline_keyboard_for_lead_with_group, main_menu_inline_keyboard_for_lead_without_group


from logger_config import get_logger

logger = get_logger()

main_menu_router: Router = Router()


@main_menu_router.message(Command("menu"))
async def main_menu_handler(message: Message, session: AsyncSession):
    user_id = message.from_user.id
    logger.debug(f"Получен запрос на главное меню от пользователя с ID: {user_id}")
    try:
        keyboard = await get_user_keyboard(session, user_id)
        logger.debug(f"Клавиатура для пользователя с ID {user_id} успешно получена.")
        await message.delete()
        await message.answer('Главное меню', reply_markup=keyboard)
        logger.info(f"Пользователю с ID {user_id} отправлено сообщение с главным меню.")
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на главное меню от пользователя с ID {user_id}: {e}")


async def get_user_keyboard(session: AsyncSession, tg_id: int):
    logger.debug(f"Получение клавиатуры для пользователя с tg_id={tg_id}")

    is_admin = check_admin(tg_id)
    logger.debug(f"Пользователь с tg_id={tg_id} является администратором: {is_admin}")

    if is_admin:
        logger.info(f"Пользователь с tg_id={tg_id} имеет доступ к администраторской клавиатуре.")
        return admin_main_menu_inline_keyboard
    else:
        try:
            user_in_db = await orm_get_user_by_tg_id(session, tg_id)
            if user_in_db is None:
                logger.warning(f"Пользователь с tg_id={tg_id} не найден в базе данных.")
                return main_menu_inline_keyboard_for_lead_without_group

            lessons = user_in_db.user_lessons
            user_crm_is_study = user_in_db.is_study

            logger.debug(f"Пользователь с tg_id={tg_id} имеет уроки: {lessons}")
            logger.debug(f"Пользователь с tg_id={tg_id} лид/клиент: {user_crm_is_study}")

            if user_crm_is_study:
                logger.info(
                    f"Пользователь с tg_id={tg_id} резидент с уроками, возвращается клавиатура для клиента.")
                return main_menu_inline_keyboard_for_client
            elif lessons:
                logger.info(f"Пользователь с tg_id={tg_id} лид и имеет уроки, возвращается клавиатура для лида с группой.")
                return main_menu_inline_keyboard_for_lead_with_group
            else:
                logger.info(
                    f"Пользователь с tg_id={tg_id} лид и не имеет уроков, возвращается клавиатура для лида без группы.")
                return main_menu_inline_keyboard_for_lead_without_group
        except Exception as e:
            logger.error(f"Ошибка при получении клавиатуры для пользователя с tg_id={tg_id}: {e}")
            return main_menu_inline_keyboard_for_lead_without_group

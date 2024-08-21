from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from crm_logic.alfa_crm_api import get_client_lessons
from database.engine import session_maker
from database.orm_query import orm_get_user_by_tg_id, get_manager_info
from tg_bot.middlewares.middleware_database import DataBaseSession

logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")


manager_contact_router: Router = Router()
manager_contact_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


@manager_contact_router.callback_query(F.data=='contact_manager' or F.data == 'work_off')
async def process_button_manager_contact_press(callback: CallbackQuery, session: AsyncSession):
    try:
        logger.info(f"Начало обработки нажатия кнопки от пользователя {callback.from_user.id}")
        await callback.message.answer(text='Секундочку, сейчас мы поищем подходящего.. 😁')
        user = await orm_get_user_by_tg_id(session, callback.from_user.id)
        if not user:
            logger.warning(f"Пользователь с tg_id {callback.from_user.id} не найден.")
            await callback.message.answer(text="Пользователь не найден в системе.")
            return

        user_branch_ids = list(map(int, user.user_branch_ids.split(',')))
        user_crm_id = user.user_crm_id
        logger.debug(f"Извлечены branch_ids: {user_branch_ids} и user_crm_id: {user_crm_id}")

        user_lessons = await get_client_lessons(user_crm_id, user_branch_ids)
        if not user_lessons.get("items"):
            logger.info(f"Уроки для пользователя с crm_id {user_crm_id} не найдены.")
            await callback.message.answer(text="Уроки не найдены.")
            return
        lesson = user_lessons.get("items", [])[0]
        lesson_address = lesson.get("room_id", 0)
        logger.debug(f"Извлечен адрес урока: {lesson_address}")
        if lesson_address:
            info = await get_manager_info(session, lesson_address)
            if info:
                answer_text = f"Ваш менеджер:\n{info.manager}\n{info.link}"
                logger.info(f"Отправка информации о менеджере пользователю {callback.from_user.id}")
                await callback.message.answer(text=answer_text)
            else:
                logger.warning(f"Менеджер для адреса {lesson_address} не найден.")
                await callback.message.answer(text="Информация о менеджере не найдена.")
        else:
            logger.warning(f"Адрес урока для CRM ID {user_crm_id} не найден.")
            await callback.message.answer(text="Адрес урока не найден.")
    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при обработке нажатия кнопки: {e}")
        await callback.message.answer(text="Произошла ошибка при обработке запроса.")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при обработке нажатия кнопки: {e}")
        await callback.message.answer(text="Произошла неизвестная ошибка.")
    finally:
        await callback.answer()
        logger.info(f"Завершение обработки нажатия кнопки от пользователя {callback.from_user.id}")


@manager_contact_router.callback_query(F.data == 'lead_contact_manager_lead')
async def process_button_lead_contact_press(callback: CallbackQuery, session: AsyncSession):
    logger.debug("Обработка нажатия кнопки 'lead_contact_manager_lead'")
    logger.debug(f"Получен запрос от пользователя: {callback.from_user.id}")

    response_text = 'Менеджер Евгений:\nhttps://t.me/EvgeniyKIBERone\n+375296332779'

    try:
        await callback.message.answer(text=response_text)
        logger.info(f"Отправлено сообщение пользователю {callback.from_user.id}: {response_text}")
        await callback.answer()
        logger.debug(f"Подтверждение нажатия кнопки отправлено пользователю {callback.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при обработке нажатия кнопки: {e}")

from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from crm_logic.alfa_crm_api import get_user_trial_lesson
from database.engine import session_maker
from database.orm_query import orm_get_user_by_tg_id
from tg_bot.middlewares.middleware_database import DataBaseSession

logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")

trial_lesson_router: Router = Router()
trial_lesson_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))

week = {
    '0': 'Понедельник',
    '1': 'Вторник',
    '2': 'Среда',
    '3': 'Четверг',
    '4': 'Пятница',
    '5': 'Суббота',
    '6': 'Воскресенье'
}

MINSK = {
    '1': "Локация разработки и тестирования ПО",
    '12': "Аэродромная, 125, 4 этаж, кабинет 29",
    '14': "Петра Мстиславца, 1, с торца",
    '15': "ТЦ Арена-Сити, Пр-т Победителей 84, 2 этаж",
    '16': "Неманская, 24, 2 этаж, кабинет 215",
    '19': "Максима Богдановича 32, 2 этаж",
}

BORISOV = {
    '18': "ТЦ Клад Наполеона, Строителей 26, 3 этаж"
}

BARANOVICHI = {
    '17': 'Тельмана, 64, 2 этаж',
    '20': "Р-н Боровки, Geely Центр, пересечение улицы Морфицкого и Журавлевича 1 А, 3 этаж"
}


@trial_lesson_router.callback_query(F.data == 'user_trial_date')
async def user_trial_handler(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    logger.debug(f"Начало обработки запроса на пробное занятие от пользователя с ID: {user_id}")

    try:
        await callback.message.edit_text(text="Ожидайте пожалуйста, проверяю Ваше расписание..")
        logger.debug(f"Сообщение пользователю с ID {user_id} изменено на 'Ожидайте...'")

        # Получаем информацию о пользователе
        user = await orm_get_user_by_tg_id(session, user_id)
        logger.debug(f"Получены данные пользователя с ID {user_id}: {user}")

        # Получаем ID филиалов пользователя
        user_branch_ids = list(map(int, user.user_branch_ids.split(',')))
        logger.debug(f"ID филиалов пользователя с ID {user_id}: {user_branch_ids}")

        # Получаем CRM ID пользователя
        user_crm_id = user.user_crm_id
        logger.debug(f"CRM ID пользователя с ID {user_id}: {user_crm_id}")

        # Получаем информацию о пробных занятиях пользователя
        user_lessons = await get_user_trial_lesson(user_crm_id, user_branch_ids)
        logger.debug(f"Получены данные о занятиях для пользователя с ID {user_id}: {user_lessons}")

        # Проверка, есть ли занятия
        if user_lessons.get("items", []):
            trial_lesson = user_lessons.get("items", [])[0]
            logger.debug(f"Пробное занятие для пользователя с ID {user_id}: {trial_lesson}")

            lesson_date = trial_lesson.get("date", None).split("-")
            logger.debug(f"Дата занятия для пользователя с ID {user_id}: {lesson_date}")

            lesson_date_splitted = datetime(int(lesson_date[0]), int(lesson_date[1]), int(lesson_date[2]))
            lesson_day = week[str(lesson_date_splitted.weekday())]
            logger.debug(f"День недели занятия для пользователя с ID {user_id}: {lesson_day}")

            lesson_time = f"{trial_lesson.get('time_from').split(' ')[1][:-3]} - {trial_lesson.get('time_to').split(' ')[1][:-3]}"
            logger.debug(f"Время занятия для пользователя с ID {user_id}: {lesson_time}")

            # Получаем адрес занятия
            lesson_address = str(trial_lesson.get("room_id", None))
            logger.debug(f"Адрес занятия для пользователя с ID {user_id}: {lesson_address}")

            if lesson_address:
                if lesson_address in MINSK:
                    lesson_address = MINSK[lesson_address]
                elif lesson_address in BORISOV:
                    lesson_address = BORISOV[lesson_address]
                elif lesson_address in BARANOVICHI:
                    lesson_address = BARANOVICHI[lesson_address]
                logger.debug(f"Адрес занятия для пользователя с ID {user_id} после обработки: {lesson_address}")

            await callback.message.answer(
                text=f'Пробный урок: \n{lesson_day}: {lesson_time}\n{lesson_address}'
            )
            logger.debug(f"Отправлено расписание пользователю с ID {user_id}: {lesson_day}, {lesson_time}, {lesson_address}")
        else:
            await callback.message.answer(text='В настоящее время у Вас нет занятий')
            logger.debug(f"Пользователь с ID {user_id} не имеет запланированных занятий")

        await callback.answer()
        logger.debug(f"Обработка запроса на пробное занятие завершена для пользователя с ID {user_id}")

    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на пробное занятие от пользователя с ID {user_id}: {e}")
        await callback.message.answer('Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.')
        await callback.answer()

    logger.debug(f"Завершение обработки запроса на пробное занятие от пользователя с ID: {user_id}")
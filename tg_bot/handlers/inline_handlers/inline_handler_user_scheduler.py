from datetime import datetime

from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from crm_logic.alfa_crm_api import find_user_by_phone, get_client_lessons
from database.engine import session_maker
from database.orm_query import orm_get_user
from tg_bot.filters.filter_admin import check_admin
from tg_bot.handlers.handler_main_menu import get_user_keyboard
from tg_bot.middlewares.middleware_database import DataBaseSession

logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")

user_scheduler_router: Router = Router()
user_scheduler_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


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


@user_scheduler_router.callback_query(F.data == 'user_scheduler')
async def process_button_inline_user_scheduler(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    logger.debug(f"Обработка запроса на расписание от пользователя с ID: {user_id}")

    if check_admin(user_id):
        logger.info(f"Пользователь с ID {user_id} является администратором, запрос на расписание проигнорирован.")
        await callback.answer()
        return

    try:
        await callback.message.answer(text='Ожидайте пожалуйста, я пока проверяю Ваше расписание..')

        user = await orm_get_user(session, user_id)
        user_branch_ids = list(map(int, user.user_branch_ids.split(',')))
        user_crm_id = user.user_crm_id
        user_lessons = await get_client_lessons(user_crm_id, user_branch_ids)

        if user_lessons.get("items", []):
            lesson = user_lessons.get("items", [])[-1]
            lesson_date = lesson.get("date", None).split("-")
            lesson_date_splitted = datetime(int(lesson_date[0]), int(lesson_date[1]), int(lesson_date[2]))
            lesson_day = week[str(lesson_date_splitted.weekday())]
            lesson_time = f"{lesson.get('time_from').split(' ')[1][:-3]} - {lesson.get('time_to').split(' ')[1][:-3]}"
            lesson_address = str(lesson.get("room_id", None))

            if lesson_address:
                if lesson_address in MINSK:
                    lesson_address = MINSK[lesson_address]
                elif lesson_address in BORISOV:
                    lesson_address = BORISOV[lesson_address]
                elif lesson_address in BARANOVICHI:
                    lesson_address = BARANOVICHI[lesson_address]

            await callback.message.answer(text=f'Ближайший урок: \n{lesson_day}: {lesson_time}\n{lesson_address}')
            logger.debug(
                f"Отправлено расписание пользователю с ID {user_id}: {lesson_day}, {lesson_time}, {lesson_address}")
        else:
            await callback.message.answer(text='В настоящее время у Вас нет занятий')
            logger.debug(f"Пользователь с ID {user_id} не имеет запланированных занятий")

        await callback.answer()
        logger.debug(f"Обработка запроса на расписание завершена для пользователя с ID {user_id}")

    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на расписание от пользователя с ID {user_id}: {e}")
        await callback.message.answer(
            'Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.'
        )
        await callback.answer()

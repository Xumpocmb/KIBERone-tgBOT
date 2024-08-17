from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from crm_logic.alfa_crm_api import get_user_trial_lesson
from database.engine import session_maker
from database.orm_query import orm_get_user
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
async def tg_links_handler(callback: CallbackQuery, session: AsyncSession):
    await callback.message.edit_text(text="Ожидайте пожалуйста, проверяю Ваше расписание..")
    user = await orm_get_user(session, callback.from_user.id)
    user_branch_ids: list = list(map(int, user.user_branch_ids.split(',')))
    user_crm_id: int = user.user_crm_id
    user_lessons = await get_user_trial_lesson(user_crm_id, user_branch_ids)

    if user_lessons.get("items", []):
        trial_lesson = user_lessons.get("items", [])[0]
        lesson_date = trial_lesson.get("date", None).split("-")
        lesson_date_splitted = datetime(int(lesson_date[0]), int(lesson_date[1]), int(lesson_date[2]))
        lesson_day = week[str(lesson_date_splitted.weekday())]
        lesson_time = f"{trial_lesson.get('time_from').split(' ')[1][:-3]} - {trial_lesson.get('time_to').split(' ')[1][:-3]}"
        lesson_address = str(trial_lesson.get("room_id", None))

        if lesson_address:
            if lesson_address in MINSK:
                lesson_address = MINSK[lesson_address]
            elif lesson_address in BORISOV:
                lesson_address = BORISOV[lesson_address]
            elif lesson_address in BARANOVICHI:
                lesson_address = BARANOVICHI[lesson_address]
        await callback.message.answer(text=f'Ближайший урок: \n{lesson_day}: {lesson_time}\n{lesson_address}')
        logger.debug("Отправлено расписание пользователю")
    else:
        await callback.message.answer(text='В настоящее время у Вас нет занятий')
        logger.debug("Отправлено сообщение пользователю")
        await callback.answer()

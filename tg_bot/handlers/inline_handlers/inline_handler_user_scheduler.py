from datetime import datetime

from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery

from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.crm_logic.alfa_crm_api import find_user_by_phone, get_client_lessons
from tg_bot.database.engine import session_maker
from tg_bot.database.orm_query import orm_get_user_by_tg_id, orm_get_location
from tg_bot.filters.filter_admin import check_admin
from tg_bot.middlewares.middleware_database import DataBaseSession


from logger_config import get_logger

logger = get_logger()

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
    '19': "Максима Богдановича 132, 2 этаж",
    "21": "Пер. Москвина 4",
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
    logger.debug(f"Начало обработки запроса на расписание от пользователя с ID: {user_id}")

    if await is_admin_user(user_id, callback):
        return

    await notify_user_processing(callback)

    user = await get_user_data(session, user_id, callback)
    if not user:
        return

    user_in_crm = await find_user_in_crm(user.phone_number, callback)
    if not user_in_crm:
        return

    await process_user_schedule(session,user_in_crm, callback)


async def is_admin_user(user_id: int, callback: CallbackQuery) -> bool:
    """Проверка, является ли пользователь администратором."""
    if check_admin(user_id):
        logger.info(f"Пользователь с ID {user_id} является администратором, запрос проигнорирован.")
        await callback.answer()
        return True
    return False


async def notify_user_processing(callback: CallbackQuery):
    """Уведомление пользователя о начале обработки запроса."""
    await callback.message.answer(
        text='Ожидайте пожалуйста, я пока проверяю Ваше расписание..\n'
             'Это занимает не больше минуты.\n'
             'Если ответ не пришел, повторите запрос еще раз.'
    )


async def get_user_data(session: AsyncSession, user_id: int, callback: CallbackQuery):
    """Получение данных пользователя из БД."""
    logger.debug(f"Получение данных пользователя с ID {user_id} из БД...")
    user = await orm_get_user_by_tg_id(session, user_id)
    if not user:
        logger.error(f"Пользователь с ID {user_id} не найден в БД.")
        await callback.message.answer('Ваши данные не найдены.')
        await callback.answer()
    return user


async def find_user_in_crm(phone_number: str, callback: CallbackQuery):
    """Поиск пользователя в CRM по номеру телефона."""
    logger.debug(f"Поиск пользователя в CRM по телефону {phone_number}...")
    user_in_crm = await find_user_by_phone(phone_number)
    if not user_in_crm:
        logger.error(f"Пользователь с телефоном {phone_number} не найден в CRM.")
        await callback.message.answer('Ваши данные в CRM не найдены.')
        await callback.answer()
    return user_in_crm


async def process_user_schedule(session, user_in_crm, callback: CallbackQuery):
    """Обработка расписания пользователя на основе данных из CRM."""
    user_crm_items = user_in_crm.get("items", [])
    logger.debug(f"Найдено {len(user_crm_items)} записей в CRM.")

    for item in user_crm_items:
        await process_single_crm_item(session, item, callback)


async def process_single_crm_item(session, item, callback: CallbackQuery):
    """Обработка одной записи из CRM."""
    user_name = item.get("name", None)
    user_branch_ids = item.get("branch_ids", [])
    user_crm_id = item.get("id")
    user_lessons = await get_client_lessons(user_crm_id, user_branch_ids)
    if user_lessons['total'] > user_lessons['count']:
        page = user_lessons['total'] // user_lessons['count']
        user_lessons = await get_client_lessons(user_crm_id, user_branch_ids, page=page)

    last_user_lesson = user_lessons.get("items", [])[-1]

    await send_lesson_info(session, last_user_lesson, user_name, callback)


async def send_lesson_info(session, last_user_lesson, student_name: str, callback: CallbackQuery):
    """Отправка информации о ближайшем занятии пользователю."""

    lesson_day, lesson_time, lesson_address = await format_lesson_info(session, last_user_lesson)
    logger.debug(f"День недели: {lesson_day}, Время: {lesson_time}, Адрес: {lesson_address}")

    lesson_date = last_user_lesson.get("lesson_date") or last_user_lesson.get("date")
    date_obj = datetime.strptime(lesson_date, "%Y-%m-%d")
    new_date_str = date_obj.strftime("%d-%m-%Y")

    await callback.message.answer(
        text=f'{student_name}\nБлижайший урок: {new_date_str}\n{lesson_day}: {lesson_time}\n{lesson_address}'
    )
    logger.debug(f"Отправлено расписание для пользователя с ID {callback.from_user.id}.")


async def format_lesson_info(session, lesson) -> tuple:
    """Форматирование данных урока для отображения."""
    lesson_date = lesson.get("lesson_date") or lesson.get("date")
    lesson_date_splitted = lesson_date.split('-')

    # Определение дня недели
    # lesson_day_of_the_week = datetime.strptime(lesson_date, "%Y-%m-%d").strftime("%A")

    lesson_day = week[str(datetime(int(lesson_date_splitted[0]), int(lesson_date_splitted[1]),
                                   int(lesson_date_splitted[2])).weekday())]

    # Форматирование времени урока
    lesson_time = f"{lesson.get('time_from').split(' ')[1][:-3]} - {lesson.get('time_to').split(' ')[1][:-3]}"

    # Определение адреса урока
    room_id = lesson.get("room_id", None)
    location_info = await orm_get_location(session, room_id)
    location_name = location_info.location_name
    location_map_link = location_info.location_map_link

    lesson_address = f"{location_name}\n{location_map_link}"

    return lesson_day, lesson_time, lesson_address

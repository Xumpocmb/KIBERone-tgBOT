import asyncio
import os
from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from tg_bot.crm_logic.alfa_crm_api import find_user_by_phone, get_user_trial_lesson, get_client_lessons
from tg_bot.database.engine import session_maker
from tg_bot.database.models import User, Locations
from tg_bot.database.orm_query import orm_update_user
from tg_bot.filters.filter_admin import check_admin

from logger_config import get_logger

logger = get_logger()

engine = create_async_engine("sqlite+aiosqlite:///tg_bot_Database.db", echo=True)
Session = async_sessionmaker(bind=engine, expire_on_commit=False)

tz = timezone('Europe/Moscow')

jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///tg_bot_Database.db')
}
scheduler = AsyncIOScheduler(jobstores=jobstores)

bot: Bot = Bot(token=os.environ.get("BOT_TOKEN"))


async def get_users_from_db():
    async with session_maker() as session:
        query = select(User)
        result = await session.execute(query)
        return result.scalars().all()


async  def orm_get_location(room_id: int):
    try:
        async with session_maker() as session:
            query = select(Locations).where(Locations.location_id == room_id)
            result = await session.execute(query)
            location = result.scalar()
            if location:
                logger.info(f"Локация с room_id {room_id} найдена: {location}")
            else:
                logger.info(f"Локация с room_id {room_id} не найдена.")
            return location
    except Exception as e:
        print(f"An error occurred: {e}")


""" BALANCE
------------------------
"""


async def check_user_balance():
    all_users = await get_users_from_db()
    for user in all_users:
        is_admin = check_admin(int(user.tg_id))
        if not is_admin:
            logger.debug(f"Проверка баланса пользователя {user.phone_number}")
            user_in_crm = await find_user_by_phone(user.phone_number)
            items = user_in_crm.get("items", [])
            if items:
                logger.debug(f"Найдено {len(items)} записей в ЦРМ.")
                for item in items:
                    if item.get("is_study", 0):
                        user_paid_lesson_count: int = int(item.get("paid_count", 0))
                        logger.debug(f"Количество оплаченных занятий: {user.phone_number}: {user_paid_lesson_count}")
                        user_balance = str(item.get("balance", 0))
                        logger.debug(f"Баланс: {user_balance}")
                        # paid_count = int(item.get("paid_count", 0))

                        async with Session() as session:
                            user_data = {
                                "tg_id": user.tg_id,
                                "balance": user_balance
                            }
                            await orm_update_user(session, user_data)
                        user_id = item.get("id", None)

                        # напоминание перед уроком
                        user_branch_ids = item.get("branch_ids", [])
                        user_lessons = await get_client_lessons(user_id, user_branch_ids)
                        if user_lessons['total'] > user_lessons['count']:
                            page = user_lessons['total'] // user_lessons['count']
                            user_lessons = await get_client_lessons(user_id, user_branch_ids, page=page)

                        last_user_lesson = user_lessons.get("items", [])[-1]

                        next_lesson_date = last_user_lesson.get("lesson_date") or last_user_lesson.get("date")
                        logger.debug(f'Дата следующего занятия для пользователя {user.phone_number}: {next_lesson_date}')
                        if next_lesson_date:
                            next_lesson_date = datetime.strptime(next_lesson_date, '%Y-%m-%d')
                            logger.debug(f'Дата следующего занятия для пользователя {user.phone_number}: {next_lesson_date}')
                            if user_paid_lesson_count <= 0:
                                await create_balance_reminder_task(user.tg_id, user_id, next_lesson_date, user_paid_lesson_count)
                                logger.debug(f'Задача для отправки напоминания пользователю {user.tg_id} на {next_lesson_date} создана.')
                            else:
                                job_id = f'balance_reminder_{user.tg_id}_{user_id}_{next_lesson_date.strftime("%Y%m%d")}'
                                existing_job = scheduler.get_job(job_id)
                                if existing_job:
                                    scheduler.remove_job(f'balance_reminder_{user.tg_id}_{user_id}_{next_lesson_date.strftime("%Y%m%d")}')

        await asyncio.sleep(5)


async def create_balance_reminder_task(tg_id, user_id, next_lesson_date, user_paid_lesson_count):
    logger.info(f'Создание задачи для пользователя {tg_id} с ID {user_id}')
    job_id = f'balance_reminder_{tg_id}_{user_id}_{next_lesson_date.strftime("%Y%m%d")}'
    existing_job = scheduler.get_job(job_id)
    if existing_job:
        logger.info(
            f'Задача для отправки напоминания пользователю {tg_id} на {next_lesson_date} уже существует.')
        return

    # trigger_time = datetime.now() + timedelta(seconds=10)
    # trigger = DateTrigger(run_date=trigger_time)

    trigger = CronTrigger(year=next_lesson_date.year, month=next_lesson_date.month, day=next_lesson_date.day,
                          hour=9, minute=0)

    scheduler.add_job(
        send_balance_reminder_message,
        trigger,
        args=[tg_id, user_id, next_lesson_date, user_paid_lesson_count],
        id=job_id,
        misfire_grace_time=3600,
    )

    logger.info(f'Задача для отправки напоминания пользователю {tg_id} на {next_lesson_date} создана.')


async def send_balance_reminder_message(tg_id, user_id, lesson_datetime, user_paid_lesson_count):
    logger.info(f'Отправляю напоминание пользователю {tg_id} о пробном занятии на {lesson_datetime}.')

    next_lesson_date = lesson_datetime.strftime('%d.%m')

    # day = lesson_datetime.day
    # logger.debug(f'День {day}')
    if user_paid_lesson_count == 0:
        reminder_message = (
            "Уважаемый клиент!\n"
            "Во избежание просрочки оплаты за обучение, просим произвести оплату через ЕРИП по "
            "ссылке https://clck.ru/36h7Df или оплатить на месте.\n"
            "Ваш KIBERone!\n")
        async with bot:
            await bot.send_message(chat_id=tg_id, text=reminder_message)
        logger.info(f'Напоминание пользователю {tg_id} о необходимости оплаты занятий {next_lesson_date} отправлено.')
    elif user_paid_lesson_count < 0:
        reminder_message = (
            "https://youtu.be/j-tUb1o6dVU \n"
            "Уважаемый клиент!\n"
            "У нас не отобразилась ваша оплата за занятия. Оплатить через ЕРИП можно "
            "по ссылке https://clck.ru/36h7Df или оплатить на месте.\n"
            "Ваш KIBERone!\n")
        async with bot:
            await bot.send_message(chat_id=tg_id, text=reminder_message)
        logger.info(f'Напоминание пользователю {tg_id} о необходимости оплаты занятий {next_lesson_date} отправлено.')



""" TRIAL LESSONS
------------------------
"""


async def check_user_trial_lesson():
    users = await get_users_from_db()
    for user in users:
        is_admin = check_admin(int(user.tg_id))
        logger.debug(f"{user.tg_id} | {is_admin}")
        if not is_admin:
            user_in_crm = await find_user_by_phone(user.phone_number)
            if user_in_crm.get("total", 0):
                items = user_in_crm.get("items", [])
                for item in items:
                    if item.get("is_study", 0) == 0:
                        user_crm_id = item.get("id", None)
                        user_branch_ids: list = item.get("branch_ids", [])
                        user_lessons = await get_user_trial_lesson(user_crm_id, user_branch_ids)
                        if user_lessons.get("total", 0) > 0:
                            trial_lesson = user_lessons.get("items", [])[0]
                            logger.debug(f"Пробное занятие для пользователя с ID {user_crm_id}: {trial_lesson}")

                            lesson_date = trial_lesson.get("date", None)
                            logger.debug(f"Дата занятия для пользователя с ID {user_crm_id}: {lesson_date}")

                            lesson_time = f"{trial_lesson.get('time_from').split(' ')[1][:-3]}"

                            room_id = trial_lesson.get("room_id", None)
                            if room_id:
                                location_info = await orm_get_location(room_id)
                                if location_info:
                                    location_name = location_info.location_name
                                    location_map_link = location_info.location_map_link
                                    lesson_address = f"{location_name}\n{location_map_link}"
                                else:
                                    lesson_address = "Неизвестно"
                            else:
                                lesson_address = "Неизвестно"

                            logger.debug(
                                f'У пользователя {user.phone_number} есть запланированные пробные занятия на {lesson_date, lesson_time}.')
                            if lesson_date and lesson_time:
                                lesson_datetime_str = f"{lesson_date} {lesson_time}"
                                lesson_datetime = datetime.strptime(lesson_datetime_str, '%Y-%m-%d %H:%M')
                                await create_trial_lesson_reminder_task(user.tg_id, user_crm_id, lesson_datetime, lesson_address)
                                logger.debug(
                                    f'Задача для отправки напоминания пользователю {user.phone_number} на {lesson_date} '
                                    f'создана.')
                            else:
                                logger.info(
                                    f'Не удалось получить дату и время пробного занятия пользователя {user.phone_number}')
                        else:
                            await asyncio.sleep(5)
                            logger.info("Не удалось получить пробное занятие. Попытка получить обычные занятия.")
                            user_lessons = await get_client_lessons(user_crm_id, user_branch_ids)
                            if user_lessons.get("total", 0) > 0:
                                logger.debug(f"Обычные занятия для пользователя {user.phone_number}: {user_lessons}")
                                user_taught_lessons = await get_client_lessons(user_crm_id, user_branch_ids, status=3)
                                logger.debug(f"Занятия, посещенные пользователем {user.phone_number}: {user_taught_lessons}")
                                if user_taught_lessons.get("total", 0) == 0:
                                    logger.debug(f"Пользователь {user.phone_number} никогда не посещал занятия.")
                                    if user_lessons.get('total', 0) > user_lessons.get('count', 0):

                                        page = user_lessons.get('total', 0) // user_lessons.get('count', 1)
                                        user_lessons = await get_client_lessons(user_crm_id, user_branch_ids, page=page)

                                        logger.debug(f"Обычные занятия для пользователя {user.phone_number}: {user_lessons}")
                                    last_user_lesson = user_lessons.get("items", [])[-1]

                                    logger.debug(f"Последнее обычное занятие для пользователя {user.phone_number}: {last_user_lesson}")

                                    next_lesson_date_str = last_user_lesson.get("lesson_date") \
                                        if last_user_lesson.get("lesson_date") \
                                        else last_user_lesson.get("date")

                                    logger.debug(f"Дата следующего обычного занятия для пользователя {user.phone_number}: {next_lesson_date_str}")
                                    lesson_time = f"{last_user_lesson.get('time_from').split(' ')[1][:-3]}"
                                    lesson_datetime_str = f"{next_lesson_date_str} {lesson_time}"

                                    next_lesson_date = datetime.strptime(lesson_datetime_str, '%Y-%m-%d %H:%M')
                                    reminder_date = next_lesson_date - timedelta(days=1)

                                    room_id = last_user_lesson.get("room_id", None)
                                    if room_id:
                                        location_info = await orm_get_location(room_id)
                                        if location_info:
                                            location_name = location_info.location_name
                                            location_map_link = location_info.location_map_link
                                            lesson_address = f"{location_name}\n{location_map_link}"
                                        else:
                                            lesson_address = "Неизвестно"
                                    else:
                                        lesson_address = "Неизвестно"

                                    logger.debug(f"Дата и время напоминания для пользователя {user.phone_number}: {reminder_date}")

                                    await create_usual_lesson_reminder_task(user.tg_id, next_lesson_date, reminder_date, lesson_address)
                                else:
                                    logger.debug(f"Пользователь {user.phone_number} уже посещал обычные занятия.")

                            logger.info(f'У пользователя {user.phone_number} нет запланированных пробных занятий. Создан таск на обычное занятие.')
                    else:
                        logger.debug(f'У пользователя {user.phone_number} is_study = 1.')
            else:
                logger.info(f'У пользователя {user.phone_number} нет запланированных пробных занятий.')
        await asyncio.sleep(7)


async def create_trial_lesson_reminder_task(tg_id, user_crm_id, lesson_date, lesson_address):
    job_id = f'trial_reminder_{tg_id}_{user_crm_id}_{lesson_date.strftime("%Y%m%d%H%M")}'
    existing_job = scheduler.get_job(job_id)

    if existing_job:
        logger.info(
            f'Задача для отправки напоминания пользователю {tg_id} на {lesson_date} уже существует.')
        return

    trigger = CronTrigger(year=lesson_date.year, month=lesson_date.month, day=lesson_date.day, hour=9, minute=0)
    # trigger_time = datetime.now() + timedelta(seconds=10)
    # trigger = DateTrigger(run_date=trigger_time)
    scheduler.add_job(
        send_reminder_message,
        trigger,
        args=[tg_id, lesson_date, lesson_address],
        id=job_id,
        misfire_grace_time=3600,
    )

    logger.info(f'Задача для отправки напоминания пользователю {tg_id} на {lesson_date} создана.')


async def create_usual_lesson_reminder_task(tg_id, next_lesson_date, reminder_date, lesson_address):
    job_id = f'usual_lesson_reminder_{tg_id}_{reminder_date.strftime("%Y%m%d")}'
    existing_job = scheduler.get_job(job_id)

    if existing_job:
        logger.info(
            f'Задача для отправки напоминания пользователю {tg_id} на {reminder_date} уже существует.')
        return

    trigger = CronTrigger(year=reminder_date.year, month=reminder_date.month, day=reminder_date.day, hour=16, minute=0)
    # trigger_time = datetime.now() + timedelta(seconds=10)
    # trigger = DateTrigger(run_date=trigger_time)
    scheduler.add_job(
        send_usual_lesson_reminder_message,
        trigger,
        args=[tg_id, next_lesson_date, reminder_date, lesson_address],
        id=job_id,
        misfire_grace_time=3600,
    )

    logger.info(f'Задача для отправки напоминания пользователю {tg_id} на {reminder_date} создана.')


async def send_reminder_message(tg_id, lesson_datetime, lesson_address):
    logger.info(f'Отправляю напоминание пользователю {tg_id} о пробном занятии на {lesson_datetime}.')

    lesson_date_str = lesson_datetime.strftime('%d.%m')
    lesson_time_str = lesson_datetime.strftime('%H:%M')

    reminder_message = f"KIBERone\nНапоминание: Ваше пробное занятие состоится {lesson_date_str} в {lesson_time_str} по адресу: {lesson_address}."
    async with bot:
        await bot.send_message(chat_id=tg_id, text=reminder_message)
    logger.info(f'Напоминание пользователю {tg_id} о пробном занятии на {lesson_datetime} отправлено.')

    job_id = f'reminder_{tg_id}_{lesson_datetime.strftime("%Y%m%d%H%M")}'
    try:
        scheduler.remove_job(job_id)
    except Exception as e:
        logger.error("Ошибка при удалении задачи. Была уже удалена.")
    logger.info(f'Задача с ID {job_id} удалена из планировщика.')


async def send_usual_lesson_reminder_message(tg_id, next_lesson_date, reminder_date, lesson_address):
    logger.info(f'Отправляю напоминание пользователю {tg_id} об обычном занятии на {next_lesson_date}.')

    lesson_date_str = next_lesson_date.strftime('%d.%m')
    lesson_time_str = next_lesson_date.strftime('%H:%M')

    reminder_message = (f"\tПоздравляем с поступлением в KIBERone 👏 \n"
f"Спешим сообщить, что завтра состоится Ваше первое занятие!\n"
f"Будем ждать Вас {lesson_date_str} в {lesson_time_str} по адресу: {lesson_address}. Пожалуйста не забудьте паспорт, для заключения договора😊\n"
f"Теперь ваш ребёнок гарантировано будет обладать самыми современными знаниями и построит успешную карьеру 💛")

    async with bot:
        await bot.send_message(chat_id=tg_id, text=reminder_message)
    logger.info(f'Напоминание пользователю {tg_id} о занятии на {next_lesson_date} отправлено.')

    job_id = f'usual_lesson_reminder_{tg_id}_{reminder_date.strftime("%Y%m%d")}'
    try:
        scheduler.remove_job(job_id)
    except Exception as e:
        logger.error("Ошибка при удалении задачи. Была уже удалена.")
    logger.info(f'Задача с ID {job_id} удалена из планировщика.')


""" BIRTHDAY
------------------------
"""

# можно проверить в БД, есть ли ДР, если нету, то уже брать в црм. уменьшит количество запросов

def check_reminder_time(b_date, year):
    r_time = None
    try:
        r_time = b_date.replace(year=year, hour=10, minute=0)
    except ValueError:
        if b_date.day == 29 and b_date.month == 2:
            r_time = b_date.replace(day=28, year=year, hour=10, minute=0)
    logger.info(f"Установлено время напоминания: {r_time}")
    return r_time


async def check_user_birthday():
    """Проверка пользователей на наличие дня рождения."""
    logger.info("Запуск проверки дней рождения пользователей.")
    users = await get_users_from_db()
    logger.info(f"Найдено {len(users)} пользователей в базе данных.")

    for user in users:
        try:
            is_admin = check_admin(int(user.tg_id))
            if is_admin:
                logger.debug(f"Пользователь {user.tg_id} является администратором, пропуск проверки.")
                continue

            logger.info(f'Поиск пользователя с телефоном {user.phone_number}')
            crm_user = await find_user_by_phone(user.phone_number)

            if crm_user.get("total", 0) > 0:
                logger.info(f'Пользователь {user.phone_number} найден в ЦРМ.')
                crm_user_items = crm_user.get("items", [])
                logger.debug(f"Найдено {len(crm_user_items)} записей для пользователя {user.phone_number}.")

                if crm_user_items:
                    for item in crm_user_items:
                        crm_user_birthday_str = item.get("dob", "")
                        crm_name = item.get("name", "")
                        crm_id = item.get("id", 0)
                        if crm_user_birthday_str:
                            crm_user_birthday = datetime.strptime(crm_user_birthday_str, '%d.%m.%Y')
                            logger.info(f'Дата рождения для пользователя {user.phone_number}: {crm_user_birthday}')
                            await create_birthday_reminder_task(user.tg_id, crm_user_birthday, crm_name, crm_id)
                        else:
                            logger.warning(f'Пользователь {user.phone_number} не имеет даты рождения в ЦРМ.')
                else:
                    logger.info(f'Для пользователя {user.phone_number} нет записей о дне рождения в ЦРМ.')
            else:
                logger.warning(f'Пользователь {user.phone_number} не найден в ЦРМ.')
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f'Ошибка при обработке пользователя с телефоном {user.phone_number}: {e}')
    logger.info("Проверка дней рождения завершена.")


async def create_birthday_reminder_task(tg_id, b_date, crm_name, crm_id):
    """Создание задачи для напоминания о дне рождения."""

    now = datetime.now()
    reminder_time = check_reminder_time(b_date, now.year)
    if reminder_time < now:
        reminder_time = check_reminder_time(b_date, now.year + 1)
    job_id = f'birthday_reminder_{tg_id}_{crm_id}_{reminder_time.strftime("%Y%m%d%H%M")}'
    existing_job = scheduler.get_job(job_id)

    if existing_job:
        logger.info(f'Задача для отправки напоминания пользователю {tg_id} на {b_date} уже существует.')
        return

    # trigger_time = datetime.now() + timedelta(seconds=10)
    # trigger = DateTrigger(run_date=trigger_time)

    trigger = CronTrigger(year=reminder_time.year, month=reminder_time.month, day=reminder_time.day,
                          hour=reminder_time.hour, minute=reminder_time.minute)
    scheduler.add_job(
        send_birthday_message,
        trigger,
        args=[tg_id, b_date, crm_name],
        id=job_id,
        misfire_grace_time=3600,
    )

    logger.info(f'Задача для отправки напоминания пользователю {tg_id} на {reminder_time} создана.')


async def send_birthday_message(tg_id, b_date, crm_name):
    """Отправка напоминания о дне рождения."""
    logger.info(f'Отправляю напоминание пользователю {tg_id} о дне рождения.')

    birthday_message = (f"Поздравляем {crm_name} с Днём Рождения!\n"
                        "Пусть всё получается, всё удается, ничего не зависает и не стоит на месте. Желаем, чтобы "
                        "жизнь была интересной и захватывающей, чтоб не было времени на грусть и тоску, обиды и "
                        "разочарования!\n Ваш KIBERone!")

    async with bot:
        await bot.send_message(chat_id=tg_id, text=birthday_message)

    logger.info(f'Напоминание пользователю {tg_id} о дне рождения отправлено.')

    reminder_time = b_date.replace(year=datetime.now().year, hour=10, minute=0)
    job_id = f'birthday_reminder_{tg_id}_{reminder_time.strftime("%Y%m%d%H%M")}'
    scheduler.remove_job(job_id)
    logger.info(f'Задача с ID {job_id} удалена из планировщика.')


"""
------------------------
"""


def setup_scheduler():
    start_scheduler()
    try:
        logger.info("Setting up scheduler...")

        existing_jobs = scheduler.get_jobs()
        if existing_jobs:
            for job in existing_jobs:
                scheduler.remove_job(job.id)
            logger.info("All existing jobs removed.")
        else:
            logger.info("No existing jobs found.")

        scheduler.add_job(
            check_user_balance,
            IntervalTrigger(hours=24, start_date=datetime.now().replace(hour=19, minute=5)),  # .replace(hour=23, minute=30)
            id='check_user_balance',
            misfire_grace_time=3600,
        )

        scheduler.add_job(
            check_user_trial_lesson,
            IntervalTrigger(hours=24, start_date=datetime.now().replace(hour=1, minute=15)),  # .replace(hour=2, minute=35)
            id='check_user_trial_lesson',
            misfire_grace_time=3600,
        )

        scheduler.add_job(
            check_user_birthday,
            IntervalTrigger(hours=24, start_date=datetime.now().replace(hour=6, minute=55)),
            id='check_user_birthday',
            misfire_grace_time=3600,
        )

        logger.info("Jobs added successfully.")
    except Exception as e:
        logger.error(f"Error setting up scheduler: {e}")


def start_scheduler():
    try:
        scheduler.start()
        logger.info("Scheduler started.")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")


def stop_scheduler():
    try:
        scheduler.shutdown()
        logger.info("Scheduler stopped.")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")

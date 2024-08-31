import asyncio
import os
from datetime import datetime

from aiogram import Bot
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from crm_logic.alfa_crm_api import find_user_by_phone, get_user_trial_lesson
from database.engine import session_maker
from database.models import User
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


""" BALANCE
------------------------
"""


async def check_user_balance():
    all_users = await get_users_from_db()
    for user in all_users:
        is_admin = check_admin(int(user.tg_id))
        if not is_admin:
            user_in_crm = await find_user_by_phone(user.phone_number)
            if user_in_crm.get("total", 0):
                items = user_in_crm.get("items", [])
                for item in items:
                    if item.get("is_study", 0):
                        user_balance: float = float(item.get("balance", 0.0))
                        user.balance = user_balance
                        user_id = item.get("id", None)
                        next_lesson_date = item.get("next_lesson_date", None)
                        if next_lesson_date:
                            next_lesson_date = datetime.strptime(next_lesson_date, '%Y-%m-%d %H:%M:%S')
                            if user_balance <= 0:
                                await create_balance_reminder_task(user.tg_id, user_id, next_lesson_date)
                            else:
                                job_id = f'balance_reminder_{user.tg_id}_{user_id}_{next_lesson_date}'
                                existing_job = scheduler.get_job(job_id)
                                if existing_job:
                                    scheduler.remove_job(f'balance_reminder_{user.tg_id}_{user_id}_{next_lesson_date}')

        await asyncio.sleep(15)


async def create_balance_reminder_task(tg_id, user_id, next_lesson_date):
    logger.info(f'Создание задачи для пользователя {tg_id} с ID {user_id}')
    job_id = f'balance_reminder_{tg_id}_{user_id}_{next_lesson_date}'
    existing_job = scheduler.get_job(job_id)
    if existing_job:
        logger.info(
            f'Задача для отправки напоминания пользователю {tg_id} на {next_lesson_date} уже существует.')
        return

    trigger = CronTrigger(year=next_lesson_date.year, month=next_lesson_date.month, day=next_lesson_date.day,
                          hour=9, minute=0)

    scheduler.add_job(
        send_balance_reminder_message,
        trigger,
        args=[tg_id, user_id, next_lesson_date],
        id=job_id,
        misfire_grace_time=3600,
    )

    logger.info(f'Задача для отправки напоминания пользователю {tg_id} на {next_lesson_date} создана.')


async def send_balance_reminder_message(tg_id, user_id, lesson_datetime):
    logger.info(f'Отправляю напоминание пользователю {tg_id} о пробном занятии на {lesson_datetime}.')

    next_lesson_date = lesson_datetime.strftime('%d.%m')

    reminder_message = (
        "Уважаемый клиент!\n"
        "Во избежание просрочки оплаты за обучение, просим произвести оплату через ЕРИП по "
        "ссылке https://clck.ru/36h7Df или оплатить на месте.\n"
        "Ваш KIBERone!")
    async with bot:
        await bot.send_message(chat_id=tg_id, text=reminder_message)
    logger.info(f'Напоминание пользователю {tg_id} о пробном занятии на {next_lesson_date} отправлено.')

    job_id = f'balance_reminder_{tg_id}_{user_id}_{next_lesson_date}'
    scheduler.remove_job(job_id)
    logger.info(f'Задача с ID {job_id} удалена из планировщика.')


"""
------------------------
"""

# TODO: когда у лида появляется группа, то выслать ссылки на ТГ


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
                            logger.debug(
                                f'У пользователя {user.phone_number} есть запланированные пробные занятия на {lesson_date, lesson_time} | {type(lesson_date)}.')
                            if lesson_date and lesson_time:
                                lesson_datetime_str = f"{lesson_date} {lesson_time}"
                                lesson_datetime = datetime.strptime(lesson_datetime_str, '%Y-%m-%d %H:%M')
                                await create_trial_lesson_reminder_task(user.tg_id, user_crm_id, lesson_datetime)
                                logger.debug(
                                    f'Задача для отправки напоминания пользователю {user.phone_number} на {lesson_date} '
                                    f'создана.')
                            else:
                                logger.info(
                                    f'Не удалось получить дату и время пробного занятия пользователя {user.phone_number}')
                        else:
                            logger.info(f'У пользователя {user.phone_number} нет запланированных пробных занятий.')
        await asyncio.sleep(10)


async def create_trial_lesson_reminder_task(tg_id, user_crm_id, lesson_date):
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
        args=[tg_id, lesson_date],
        id=job_id,
        misfire_grace_time=3600,
    )

    logger.info(f'Задача для отправки напоминания пользователю {tg_id} на {lesson_date} создана.')


async def send_reminder_message(tg_id, lesson_datetime):
    logger.info(f'Отправляю напоминание пользователю {tg_id} о пробном занятии на {lesson_datetime}.')

    lesson_date_str = lesson_datetime.strftime('%d.%m')
    lesson_time_str = lesson_datetime.strftime('%H:%M')

    reminder_message = f"KIBERone\nНапоминание: Ваше пробное занятие состоится {lesson_date_str} в {lesson_time_str}."
    async with bot:
        await bot.send_message(chat_id=tg_id, text=reminder_message)
    logger.info(f'Напоминание пользователю {tg_id} о пробном занятии на {lesson_datetime} отправлено.')

    job_id = f'reminder_{tg_id}_{lesson_datetime.strftime("%Y%m%d%H%M")}'
    scheduler.remove_job(job_id)
    logger.info(f'Задача с ID {job_id} удалена из планировщика.')


""" BIRTHDAY
------------------------
"""

def check_reminder_time(b_date, year):
    r_time = None
    try:
        r_time = b_date.replace(year=year, hour=10, minute=0)
    except ValueError:
        if b_date.day == 29 and b_date.month == 2:
            r_time = b_date.replace(day=28, year=year, hour=10, minute=0)
    logger.error(f"Время напоминания некорректное: {r_time}")
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
            await asyncio.sleep(15)
        except Exception as e:
            logger.error(f'Ошибка при обработке пользователя с телефоном {user.phone_number}: {e}')
    logger.info("Проверка дней рождения завершена.")


async def create_birthday_reminder_task(tg_id, b_date, crm_name, crm_id):
    """Создание задачи для напоминания о дне рождения."""

    now = datetime.now()
    reminder_time = b_date.replace(year=datetime.now().year, hour=10, minute=0)
    if reminder_time < now:
        reminder_time = reminder_time.replace(year=now.year + 1)
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
        job_ids = ['check_user_birthday']

        existing_jobs = scheduler.get_jobs()
        if existing_jobs:
            for job in existing_jobs:
                logger.info(f"Removing existing job with ID '{job.id}'...")
                scheduler.remove_job(job.id)
            logger.info("All existing jobs removed.")
        else:
            logger.info("No existing jobs found.")

        scheduler.add_job(
            check_user_balance,
            IntervalTrigger(hours=24, start_date=datetime.now().replace(hour=23, minute=30)),
            id='check_user_balance',
            misfire_grace_time=3600,
        )

        scheduler.add_job(
            check_user_trial_lesson,
            IntervalTrigger(hours=24, start_date=datetime.now().replace(hour=2, minute=35)),
            id='check_user_trial_lesson',
            misfire_grace_time=3600,
        )

        scheduler.add_job(
            check_user_birthday,
            IntervalTrigger(hours=24, start_date=datetime.now().replace(hour=5, minute=45)),
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

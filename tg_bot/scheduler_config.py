import os
from datetime import datetime, timedelta

from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from aiogram import Bot
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from crm_logic.alfa_crm_api import find_user_by_phone
from database.engine import session_maker
from database.models import User
from tg_bot.filters.filter_admin import check_admin

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

            if crm_user:
                logger.info(f'Пользователь {user.phone_number} найден в ЦРМ.')
                crm_user_items = crm_user.get("items", [])
                logger.debug(f"Найдено {len(crm_user_items)} записей для пользователя {user.phone_number}.")

                if crm_user_items:
                    for item in crm_user_items:
                        crm_user_birthday_str = item.get("dob", "")
                        if crm_user_birthday_str:
                            crm_user_birthday = datetime.strptime(crm_user_birthday_str, '%d.%m.%Y')
                            logger.info(f'Дата рождения для пользователя {user.phone_number}: {crm_user_birthday}')
                            await create_birthday_reminder_task(user.tg_id, crm_user_birthday)
                        else:
                            logger.warning(f'Пользователь {user.phone_number} не имеет даты рождения в ЦРМ.')
                else:
                    logger.info(f'Для пользователя {user.phone_number} нет записей о дне рождения в ЦРМ.')
            else:
                logger.warning(f'Пользователь {user.phone_number} не найден в ЦРМ.')

        except Exception as e:
            logger.error(f'Ошибка при обработке пользователя с телефоном {user.phone_number}: {e}')

    logger.info("Проверка дней рождения завершена.")


async def create_birthday_reminder_task(tg_id, b_date):
    """Создание задачи для напоминания о дне рождения."""
    reminder_time = b_date.replace(year=datetime.now().year, hour=10, minute=0)
    job_id = f'birthday_reminder_{tg_id}_{reminder_time.strftime("%Y%m%d%H%M")}'
    existing_job = scheduler.get_job(job_id)

    if existing_job:
        logger.info(f'Задача для отправки напоминания пользователю {tg_id} на {b_date} уже существует.')
        return


    # trigger_time = datetime.now() + timedelta(seconds=10)
    # trigger = DateTrigger(run_date=trigger_time)

    trigger = CronTrigger(year=datetime.now().year, month=reminder_time.month, day=reminder_time.day,
                          hour=reminder_time.hour, minute=reminder_time.minute)
    scheduler.add_job(
        send_birthday_message,
        trigger,
        args=[tg_id, b_date],
        id=job_id,
        misfire_grace_time=3600,
    )

    logger.info(f'Задача для отправки напоминания пользователю {tg_id} на {reminder_time} создана.')


async def send_birthday_message(tg_id, b_date):
    """Отправка напоминания о дне рождения."""
    logger.info(f'Отправляю напоминание пользователю {tg_id} о дне рождения.')

    b_date_str = b_date.strftime('%d.%m.%Y')
    birthday_message = f"KIBERone\nДень рождения: {b_date_str}"

    async with bot:
        await bot.send_message(chat_id=tg_id, text=birthday_message)

    logger.info(f'Напоминание пользователю {tg_id} о дне рождения отправлено.')


def setup_scheduler():
    start_scheduler()
    try:
        logger.info("Setting up scheduler...")
        job_ids = ['check_user_birthday']

        for job in job_ids:
            existing_job = scheduler.get_job(job)
            if existing_job:
                logger.info(f"Job with ID '{job}' already exists. Removing...")
                scheduler.remove_job(job)
                logger.info("Existing job removed.")
            else:
                logger.info(f"No existing job with ID '{job}' found.")

        # scheduler.add_job(
        #     update_users_info,
        #     IntervalTrigger(minutes=120, start_date=datetime.now() + timedelta(minutes=40)),
        #     id='update_users_info',
        #     misfire_grace_time=3600,
        # )

        # scheduler.add_job(
        #     check_user_trial_lesson,
        #     IntervalTrigger(minutes=60, start_date=datetime.now() + timedelta(minutes=10)),
        #     id='check_user_trial_lesson',
        #     misfire_grace_time=3600,
        # )

        scheduler.add_job(
            check_user_birthday,
            IntervalTrigger(days=1, start_date=datetime.now() + timedelta(seconds=20)),
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

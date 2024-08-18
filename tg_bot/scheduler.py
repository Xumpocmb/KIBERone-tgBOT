import asyncio
import os

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta

from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone
from loguru import logger
from sqlalchemy import select

from crm_logic.alfa_crm_api import check_client_balance_from_crm, get_user_trial_lesson
from database.engine import session_maker
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from database.models import User
from tg_bot.filters.filter_admin import check_admin

engine = create_async_engine("sqlite+aiosqlite:///tg_bot_Database.db", echo=True)
Session = async_sessionmaker(bind=engine, expire_on_commit=False)


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


async def test_check_user_balance():
    logger.info('Task executed: проверка баланса пользователя.')
    users = await get_users_from_db()
    if users:
        async with session_maker() as session:
            for user in users:
                logger.info(f'Проверяю баланс пользователя {user.phone_number}')
                is_study = user.is_study
                user_branch_ids = list(map(int, user.user_branch_ids.split(',')))
                user_balance = await check_client_balance_from_crm(user.phone_number, user_branch_ids, is_study)
                logger.debug(f'Баланс пользователя {user.phone_number}: {user_balance}')
                if not user_balance:
                    user_balance = "0"
                user.balance = user_balance
                session.add(user)
                await session.commit()
                logger.info(f'Баланс пользователя {user.phone_number} обновлен.')
                await asyncio.sleep(10)
        logger.info('Проверка баланса пользователей завершена.')
    else:
        logger.info('Пользователи пока не были найдены.')


async def check_user_trial_lesson():
    users = await get_users_from_db()
    for user in users:
        is_admin = check_admin(int(user.tg_id))
        logger.debug(f"{user.tg_id} | {is_admin}")
        if not is_admin:
            if user.is_study == 0:
                user_crm_id = user.user_crm_id
                user_branch_ids = list(map(int, user.user_branch_ids.split(',')))
                user_lessons = await get_user_trial_lesson(user_crm_id, user_branch_ids)
                if user_lessons.get("items", []):
                    trial_lesson = user_lessons.get("items", [])[0]
                    lesson_date = trial_lesson.get("date", None)
                    lesson_time = f"{trial_lesson.get('time_from').split(' ')[1][:-3]}"
                    logger.debug(f'У пользователя {user.phone_number} есть запланированные пробные занятия на {lesson_date, lesson_time} | {type(lesson_date)}.')
                    if lesson_date and lesson_time:
                        lesson_datetime_str = f"{lesson_date} {lesson_time}"
                        lesson_datetime = datetime.strptime(lesson_datetime_str, '%Y-%m-%d %H:%M')
                        await create_lesson_reminder_task(user.tg_id, lesson_datetime)
                        logger.debug(f'Задача для отправки напоминания пользователю {user.phone_number} на {lesson_date} создана.')
                else:
                    logger.info(f'У пользователя {user.phone_number} нет запланированных пробных занятий.')


async def create_lesson_reminder_task(tg_id, lesson_date):
    job_id = f'reminder_{tg_id}_{lesson_date.strftime("%Y%m%d%H%M")}'
    existing_job = scheduler.get_job(job_id)

    if existing_job:
        logger.info(
            f'Задача для отправки напоминания пользователю {tg_id} на {lesson_date} уже существует.')
        return

    # trigger = CronTrigger(year=lesson_date.year, month=lesson_date.month, day=lesson_date.day, hour=9, minute=0)
    trigger_time = datetime.now() + timedelta(seconds=10)
    trigger = DateTrigger(run_date=trigger_time)
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

    lesson_date_str = lesson_datetime.strftime('%Y-%m-%d')
    lesson_time_str = lesson_datetime.strftime('%H:%M')

    reminder_message = f"KIBERone\nНапоминание: ваше пробное занятие состоится {lesson_date_str} в {lesson_time_str}."
    async with bot:
        await bot.send_message(chat_id=tg_id, text=reminder_message)
    logger.info(f'Напоминание пользователю {tg_id} о пробном занятии на {lesson_datetime} отправлено.')

def setup_scheduler():
    start_scheduler()
    try:
        logger.info("Setting up scheduler...")
        job_ids = ['test_check_user_balance', 'check_user_trial_lesson']

        for job in job_ids:
            existing_job = scheduler.get_job(job)
            logger.debug(f"Existing job: {existing_job}")

            if existing_job:
                logger.info(f"Job with ID '{job}' already exists. Removing...")
                scheduler.remove_job(job)
                logger.info("Existing job removed.")
            else:
                logger.info(f"No existing job with ID '{job}' found.")

        # scheduler.add_job(
        #     test_check_user_balance,
        #     IntervalTrigger(minutes=30, start_date=datetime.now() + timedelta(seconds=10)),
        #     id=job,
        #     misfire_grace_time=None,
        # )

        scheduler.add_job(
            check_user_trial_lesson,
            IntervalTrigger(minutes=60, start_date=datetime.now() + timedelta(seconds=10)),
            id='check_user_trial_lesson',
            misfire_grace_time=None,
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

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

from crm_logic.alfa_crm_api import check_client_balance_from_crm, get_user_trial_lesson, find_user_by_phone
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


async def update_users_info():
    logger.info('Task executed: обновление информации о пользователях.')
    users = await get_users_from_db()
    if users:
        async with session_maker() as session:
            for user in users:
                is_admin = check_admin(int(user.tg_id))
                if not is_admin:
                    logger.info(f'Поиск пользователя {user.phone_number}')
                    crm_user = await find_user_by_phone(user.phone_number)

                    if crm_user:
                        logger.info(f'Пользователь {user.phone_number} найден в ЦРМ')
                        crm_user_is_study: int = crm_user.get("items", [])[0].get("is_study", 0)
                        crm_user_balance: str = crm_user.get("items", [])[0].get("balance", "0")
                        crm_user_next_lesson_date: str = crm_user.get("items", [])[0].get("next_lesson_date", "")
                        crm_user_paid_lesson_count: int = crm_user.get("items", [])[0].get("paid_lesson_count", 0)

                        user.is_study = crm_user_is_study
                        user.balance = crm_user_balance
                        user.next_lesson_date = crm_user_next_lesson_date
                        user.paid_lesson_count = crm_user_paid_lesson_count
                        logger.info(f'Обновляю информацию о пользователе {user.phone_number}')
                        session.add(user)
                        await session.commit()
                        logger.info(f'Информация о пользователе {user.phone_number} обновлена.')

                        if crm_user_paid_lesson_count == 0:
                            lesson_datetime = datetime.strptime(crm_user_next_lesson_date, '%Y-%m-%d %H:%M')
                            await create_payment_reminder_task(user.tg_id, lesson_datetime)

                        await asyncio.sleep(10)
                    else:
                        logger.info(f'Пользователь {user.phone_number} не найден в ЦРМ')
                        await asyncio.sleep(10)
            logger.info('Обновление информации о пользователях завершено.')
    else:
        logger.info('Нет пользователей в базе данных')


async def create_payment_reminder_task(tg_id, lesson_date):
    job_id = f'payment_reminder_{tg_id}_{lesson_date.strftime("%Y%m%d%H%M")}'
    existing_job = scheduler.get_job(job_id)

    if existing_job:
        logger.info(
            f'Задача для отправки напоминания пользователю {tg_id} на {lesson_date} уже существует.')
        return

    trigger = CronTrigger(year=lesson_date.year, month=lesson_date.month, day=lesson_date.day, hour=10, minute=0)
    scheduler.add_job(
        send_payment_reminder_message,
        trigger,
        args=[tg_id],
        id=job_id,
        misfire_grace_time=3600,
    )

    logger.info(f'Задача для отправки напоминания пользователю {tg_id} на {lesson_date} создана.')


async def send_payment_reminder_message(tg_id):
    logger.info(f'Отправляю напоминание пользователю {tg_id} о необходимости оплаты занятий.')

    reminder_message = ("Уважаемый клиент!\n"
                        "Во избежание просрочки оплаты за обучение, просим произвести оплату через ЕРИП по ссылке https://clck.ru/36h7Df или оплатить на месте.)\n"
                        "Ваш KIBERone!")
    async with bot:
        await bot.send_message(chat_id=tg_id, text=reminder_message)
    logger.info(f'Напоминание пользователю {tg_id} о необходимости оплаты занятий отправлено.')


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
                    lesson_date = trial_lesson.get("lesson_date", None)
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
        job_ids = ['update_users_info', 'check_user_trial_lesson']

        for job in job_ids:
            existing_job = scheduler.get_job(job)
            logger.debug(f"Existing job: {existing_job}")

            if existing_job:
                logger.info(f"Job with ID '{job}' already exists. Removing...")
                scheduler.remove_job(job)
                logger.info("Existing job removed.")
            else:
                logger.info(f"No existing job with ID '{job}' found.")

        scheduler.add_job(
            update_users_info,
            IntervalTrigger(minutes=120, start_date=datetime.now() + timedelta(minutes=40)),
            id='update_users_info',
            misfire_grace_time=3600,
        )

        scheduler.add_job(
            check_user_trial_lesson,
            IntervalTrigger(minutes=60, start_date=datetime.now() + timedelta(minutes=10)),
            id='check_user_trial_lesson',
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

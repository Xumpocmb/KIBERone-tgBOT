from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta

from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone
from loguru import logger
from sqlalchemy import select

from crm_logic.alfa_crm_api import check_client_balance_from_crm
from database.engine import session_maker
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from database.models import User

engine = create_async_engine("sqlite+aiosqlite:///tg_bot_Database.db", echo=True)
Session = async_sessionmaker(bind=engine, expire_on_commit=False)


jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///tg_bot_Database.db')
}
scheduler = AsyncIOScheduler(jobstores=jobstores)


async def get_users_from_db():
    async with session_maker() as session:
        query = select(User)
        result = await session.execute(query)
        return result.scalars().all()


async def test_check_user_balance():
    logger.info('Task executed: проверка баланса пользователя.')
    users = await get_users_from_db()
    if users:
        for user in users:
            logger.info(f'Проверяю баланс пользователя {user.phone_number}')
            # создать таск на каждого пользователя
            # 1 баланс пользователя, 2 пробник, 3 д.р.
    else:
        logger.info('Пользователи пока не были найдены.')



def setup_scheduler():
    start_scheduler()
    try:
        logger.info("Setting up scheduler...")
        job_id = 'test_check_user_balance'
        existing_job = scheduler.get_job(job_id)
        logger.debug(f"Existing job: {existing_job}")

        if existing_job:
            logger.info(f"Job with ID '{job_id}' already exists. Removing...")
            scheduler.remove_job(job_id)
            logger.info("Existing job removed.")
        else:
            logger.info(f"No existing job with ID '{job_id}' found.")
        scheduler.add_job(
            test_check_user_balance,
            IntervalTrigger(seconds=15, start_date=datetime.now() + timedelta(seconds=10)),
            id=job_id,
            misfire_grace_time=None,
        )
        logger.info("Job added successfully.")
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

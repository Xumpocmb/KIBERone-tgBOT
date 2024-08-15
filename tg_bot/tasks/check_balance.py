# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.triggers.cron import CronTrigger
# from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
# from loguru import logger
# from crm_logic.alfa_crm_api import check_client_balance_from_crm
#
#
#
# jobstores = {
#     'default': SQLAlchemyJobStore(url='sqlite:///tg_bot_Database.db')
# }
#
# scheduler = AsyncIOScheduler(jobstores=jobstores)
#
#
# async def check_user_balance():
#     balance = await check_client_balance_from_crm("+375(47)862-48-44")
#     logger.info(f'Баланс пользователя: {balance}')
#
# scheduler.add_job(check_user_balance, CronTrigger(day_of_week='wed', hour=23, minute=26, timezone=timezone('Europe/Moscow')))
# scheduler.start()
# from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
# from datetime import datetime, timedelta

# from loguru import logger
# from apscheduler.job import Job
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
#
# from database.models import ScheduledTasks
#
# jobstores = {
#     'default': SQLAlchemyJobStore(url='sqlite:///jobs.db')  # replace with your database file path
# }
#
# scheduler = AsyncIOScheduler(jobstores=jobstores)

# scheduler = AsyncIOScheduler()
#
# logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")
# from crm_logic.alfa_crm_api import check_client_balance_from_crm


# async def check_user_balance():
#     balance = await check_client_balance_from_crm("+375(47)862-48-44")
#     logger.info(f'Баланс пользователя: {balance}')


# async def check_user_statuses_in_crm():
#     logger.info('Проверка статусов пользователей..')
#     logger.info('Проверка статусов пользователей завершена.')


# scheduler.add_job(check_user_balance, 'interval', seconds=15, next_run_time=datetime.now() + timedelta(seconds=10))
# logger.debug('Задача добавлена.')
# scheduler.add_job(check_user_statuses_in_crm, CronTrigger(day_of_week='wed', hour=23, minute=26, timezone=timezone('Europe/Moscow')))

# scheduler.start()


# scheduler.add_job(check_user_statuses_in_crm, CronTrigger(day_of_week='wed', hour=23, minute=26, timezone=timezone('Europe/Moscow')))
# task = ScheduledTasks.insert().values(
#     name='check_user_statuses_in_crm',
#     trigger='cron',
#     next_run_time=scheduler.get_job('check_user_statuses_in_crm').next_run_time
# )
#
# def create_tasks():
#     # get all clients from database
#     clients = session.query(Clients).all()
#     # create a scheduler
#     scheduler = AsyncIOScheduler()
#     # loop through clients and create tasks
#     for client in clients:
#         day, time = get_schedule(client.api_id)
#         if day and time:
#             job = scheduler.add_job(
#                 check_user_statuses_in_crm,
#                 CronTrigger(day_of_week=day, hour=time.hour, minute=time.minute, timezone=timezone('Europe/Moscow'))
#             )
#             # store the job in the database
#             job_store.add_job(job)
#     # start the scheduler
#     scheduler.start()
#
#
# def get_jobs():
#     # get all jobs from database
#     jobs = session.query(Jobs).all()
#     # loop through jobs and print their information
#     for job in jobs:
#         print(job.name, job.trigger, job.next_run_time)
#
# def pause_job(name):
#     # pause the job with the given name
#     job = scheduler.get_job(name)
#     if job:
#         scheduler.pause_job(job.id)
#         # update the job in the database
#         job_store.update_job(job, paused=True)
#
# def resume_job(name):
#     # resume the job with the given name
#     job = scheduler.get_job(name)
#     if job:
#         scheduler.resume_job(job.id)
#         # update the job in the database
#         job_store.update_job(job, paused=False)
#
# def delete_job(name):
#     # delete the job with the given name
#     job = scheduler.get_job(name)
#     if job:
#         scheduler.delete_job(job.id)
#         # delete the job from the database
#         job_store.delete_job(job)
#
# def update_job(name, new_trigger):
#     # update the job with the given name
#     job = scheduler.get_job(name)
#     if job:
#         scheduler.update_job(job.id, trigger=new_trigger)
#         # update the job in the database
#         job_store.update_job(job, trigger=new_trigger)
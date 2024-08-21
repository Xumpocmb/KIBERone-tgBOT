import os
from datetime import datetime

from aiogram import Bot
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from crm_logic.alfa_crm_api import get_user_trial_lesson
from tg_bot.filters.filter_admin import check_admin
from tg_bot.scheduler_config import scheduler, get_users_from_db

bot: Bot = Bot(token=os.environ.get("BOT_TOKEN"))



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
                        await create_trial_lesson_reminder_task(user.tg_id, lesson_datetime)
                        logger.debug(f'Задача для отправки напоминания пользователю {user.phone_number} на {lesson_date} создана.')
                else:
                    logger.info(f'У пользователя {user.phone_number} нет запланированных пробных занятий.')


async def create_trial_lesson_reminder_task(tg_id, lesson_date):
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
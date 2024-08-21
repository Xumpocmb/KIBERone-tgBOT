# import os
# from datetime import datetime, timedelta
#
# from aiogram import Bot
# from apscheduler.triggers.date import DateTrigger
# from loguru import logger
#
# from crm_logic.alfa_crm_api import find_user_by_phone
# from tg_bot.filters.filter_admin import check_admin
# from tg_bot.scheduler_config import scheduler, get_users_from_db

# bot: Bot = Bot(token=os.environ.get("BOT_TOKEN"))
#
#
# async def check_user_birthday():
#     users = await get_users_from_db()
#     for user in users:
#         is_admin = check_admin(int(user.tg_id))
#         if not is_admin:
#             logger.info(f'Поиск пользователя {user.phone_number}')
#             crm_user = await find_user_by_phone(user.phone_number)
#
#             if crm_user:
#                 logger.info(f'Пользователь {user.phone_number} найден в ЦРМ')
#                 crm_user_items = crm_user.get("items", [])
#                 if crm_user_items:
#                     for item in crm_user_items:
#                         crm_user_birthday = item.get("dob", "")
#                         if crm_user_birthday:
#                             await create_birthday_reminder_task(user.tg_id, crm_user_birthday)
#                         else:
#                             logger.info(f'Пользователь {user.phone_number} не имеет даты рождения в ЦРМ')
#             else:
#                 logger.info(f'Пользователь {user.phone_number} не найден в ЦРМ')
#
#
# async def create_birthday_reminder_task(tg_id, b_date):
#     job_id = f'birthday_reminder_{tg_id}_{b_date.strftime("%Y%m%d%H%M")}'
#     existing_job = scheduler.get_job(job_id)
#
#     if existing_job:
#         logger.info(
#             f'Задача для отправки напоминания пользователю {tg_id} на {b_date} уже существует.')
#         return
#
#     # trigger = CronTrigger(year=b_date.year, month=b_date.month, day=b_date.day, hour=10, minute=0)
#     trigger_time = datetime.now() + timedelta(seconds=10)
#     trigger = DateTrigger(run_date=trigger_time)
#     scheduler.add_job(
#         send_birthday_reminder_message,
#         trigger,
#         args=[tg_id, b_date],
#         id=job_id,
#         misfire_grace_time=3600,
#     )
#
#     logger.info(f'Задача для отправки напоминания пользователю {tg_id} на {b_date} создана.')
#
#
# async def send_birthday_reminder_message(tg_id, b_date):
#     logger.info(f'Отправляю напоминание пользователю {tg_id} о дней рождения.')
#
#     b_date_str = b_date.strftime('%d.%m.%Y')
#     birthday_message = f"KIBERone\nДень рождения: {b_date_str}"
#     async with bot:
#         await bot.send_message(chat_id=tg_id, text=birthday_message)
#     logger.info(f'Напоминание пользователю {tg_id} о дней рождения отправлено.')


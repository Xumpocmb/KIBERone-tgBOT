# async def update_users_info():
#     logger.info('Task executed: обновление информации о пользователях.')
#     users = await get_users_from_db()
#     if users:
#         async with session_maker() as session:
#             for user in users:
#                 is_admin = check_admin(int(user.tg_id))
#                 if not is_admin:
#                     logger.info(f'Поиск пользователя {user.phone_number}')
#                     crm_user = await find_user_by_phone(user.phone_number)
#
#                     if crm_user:
#                         logger.info(f'Пользователь {user.phone_number} найден в ЦРМ')
#                         crm_user_is_study: int = crm_user.get("items", [])[0].get("is_study", 0)
#                         crm_user_balance: str = crm_user.get("items", [])[0].get("balance", "0")
#                         crm_user_next_lesson_date: str = crm_user.get("items", [])[0].get("next_lesson_date", "")
#                         crm_user_paid_lesson_count: int = crm_user.get("items", [])[0].get("paid_lesson_count", 0)
#
#                         user.is_study = crm_user_is_study
#                         user.balance = crm_user_balance
#                         user.next_lesson_date = crm_user_next_lesson_date
#                         user.paid_lesson_count = crm_user_paid_lesson_count
#                         logger.info(f'Обновляю информацию о пользователе {user.phone_number}')
#                         session.add(user)
#                         await session.commit()
#                         logger.info(f'Информация о пользователе {user.phone_number} обновлена.')
#
#                         if crm_user_paid_lesson_count == 0:
#                             lesson_datetime = datetime.strptime(crm_user_next_lesson_date, '%Y-%m-%d %H:%M')
#                             await create_payment_reminder_task(user.tg_id, lesson_datetime)
#
#                         await asyncio.sleep(10)
#                     else:
#                         logger.info(f'Пользователь {user.phone_number} не найден в ЦРМ')
#                         await asyncio.sleep(10)
#             logger.info('Обновление информации о пользователях завершено.')
#     else:
#         logger.info('Нет пользователей в базе данных')
#
#
#
# async def create_payment_reminder_task(tg_id, lesson_date):
#     job_id = f'payment_reminder_{tg_id}_{lesson_date.strftime("%Y%m%d%H%M")}'
#     existing_job = scheduler.get_job(job_id)
#
#     if existing_job:
#         logger.info(
#             f'Задача для отправки напоминания пользователю {tg_id} на {lesson_date} уже существует.')
#         return
#
#     trigger = CronTrigger(year=lesson_date.year, month=lesson_date.month, day=lesson_date.day, hour=10, minute=0)
#     scheduler.add_job(
#         send_payment_reminder_message,
#         trigger,
#         args=[tg_id],
#         id=job_id,
#         misfire_grace_time=3600,
#     )
#
#     logger.info(f'Задача для отправки напоминания пользователю {tg_id} на {lesson_date} создана.')
#
#
# async def send_payment_reminder_message(tg_id):
#     logger.info(f'Отправляю напоминание пользователю {tg_id} о необходимости оплаты занятий.')
#
#     reminder_message = ("Уважаемый клиент!\n"
#                         "Во избежание просрочки оплаты за обучение, просим произвести оплату через ЕРИП по ссылке https://clck.ru/36h7Df или оплатить на месте.)\n"
#                         "Ваш KIBERone!")
#     async with bot:
#         await bot.send_message(chat_id=tg_id, text=reminder_message)
#     logger.info(f'Напоминание пользователю {tg_id} о необходимости оплаты занятий отправлено.')
#




# async def create_payment_reminder_task(tg_id, lesson_date):
#     job_id = f'payment_reminder_{tg_id}_{lesson_date.strftime("%Y%m%d%H%M")}'
#     existing_job = scheduler.get_job(job_id)
#
#     if existing_job:
#         logger.info(
#             f'Задача для отправки напоминания пользователю {tg_id} на {lesson_date} уже существует.')
#         return
#
#     trigger = CronTrigger(year=lesson_date.year, month=lesson_date.month, day=lesson_date.day, hour=10, minute=0)
#     scheduler.add_job(
#         send_payment_reminder_message,
#         trigger,
#         args=[tg_id],
#         id=job_id,
#         misfire_grace_time=3600,
#     )
#
#     logger.info(f'Задача для отправки напоминания пользователю {tg_id} на {lesson_date} создана.')
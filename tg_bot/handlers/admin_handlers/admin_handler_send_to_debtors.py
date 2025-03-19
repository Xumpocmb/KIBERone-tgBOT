import asyncio
import os

from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.crm_logic.alfa_crm_api import check_client_balance_from_crm, get_client_lessons
from tg_bot.database.engine import session_maker
from tg_bot.database.orm_query import get_all_users
from tg_bot.keyboards.inline_keyboards.inline_admin_main_menu import admin_main_menu_inline_keyboard
from tg_bot.middlewares.middleware_database import DataBaseSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv

load_dotenv()

admins_list: list = os.getenv("ADMINS").split(",")

admin_send_to_debtors: Router = Router()
admin_send_to_debtors.callback_query.middleware(DataBaseSession(session_pool=session_maker))


@admin_send_to_debtors.callback_query((F.from_user.id in admins_list) & (F.data == "admin_send_to_debtors"))
async def send_to_debtors(callback: CallbackQuery, session: AsyncSession):
    bot = callback.bot
    try:
        users_in_db = await get_all_users(session)
        logger.info(f"Получено {len(users_in_db)} пользователей из базы данных.")

        debtors_text = ("Уважаемый клиент! У нас не отобразилась ваша оплата за занятия.\n"
                        "Оплатить через ЕРИП можно по ссылке https://clck.ru/36h7Df или оплатить на месте.\n"
                        "Ваш KIBERone!")

        await callback.answer()
        await callback.message.answer("Рассылка запущена.. Она будет длиться долгое время.. В конце будет получен отчет.")

        good_send, bad_send, bad_send_list = await broadcast_message(bot=bot, users=users_in_db, text=debtors_text)
        logger.info(f"Рассылка завершена. Успешно отправлено: {good_send}, неудачно: {bad_send}.")

        await callback.message.answer(
            f'Рассылка завершена. \n'
            f'Сообщение получило <b>{good_send}</b>\n'
            f'НЕ получило <b>{bad_send}</b> пользователей.\n'
            f'список пользователей, которые заблокировали бота:\n'
            f'{'\n'.join(bad_send_list)}',
            reply_markup=admin_main_menu_inline_keyboard
        )

    except Exception as e:
        logger.error(f"Произошла ошибка при обработке коллбэка: {e}")


async def broadcast_message(bot, users, text: str = None):
    good_send = 0
    bad_send = 0
    bad_send_list = []

    for user in users:
        logger.info(f"Обработка пользователя {user.tg_id} ({user.phone_number}).")

        if user.tg_id not in admins_list:
            logger.debug(f"Пользователь {user.tg_id} не является администратором.")

            user_branch_ids = list(map(int, user.user_branch_ids))
            logger.debug(f"User branch IDs для пользователя {user.tg_id}: {user_branch_ids}.")

            if user.phone_number and user_branch_ids and user.is_study == 1:
                logger.info(f"Пользователь {user.tg_id} проходит проверку на наличие данных.")

                user_lessons = await get_client_lessons(user.user_crm_id, user_branch_ids, None, 1)
                logger.debug(f"Занятия пользователя {user.tg_id}: {user_lessons['total']}.")

                if user_lessons['total'] > 0:
                    logger.info(f"Пользователь {user.tg_id} имеет запланированные занятия.")
                    user_paid_count = await check_client_balance_from_crm(user.phone_number, user_branch_ids,
                                                                          user.is_study, True)
                    logger.debug(f"Баланс пользователя {user.tg_id}: {user_paid_count}.")

                    if user_paid_count < 0:
                        logger.debug(f"Пользователь {user.phone_number} является должником.")

                        try:
                            chat_id = user.tg_id
                            await bot.send_message(chat_id=chat_id, text=text)
                            good_send += 1
                            logger.info(f"Сообщение о задолженности успешно отправлено пользователю {user.phone_number}.")
                        except Exception as e:
                            logger.error(f"Не удалось отправить сообщение пользователю {user.phone_number}: {e}")
                            bad_send += 1
                            bad_send_list.append(user.phone_number)
                        finally:
                            await asyncio.sleep(0.5)
            else:
                logger.info(f"Пользователь {user.tg_id} не прошел проверку на наличие данных.")
        else:
            logger.info(f"Пользователь {user.tg_id} является администратором и пропущен.")

    logger.info(f"Итоги рассылки: успешно отправлено {good_send}, неудачно {bad_send}.")
    return good_send, bad_send, bad_send_list

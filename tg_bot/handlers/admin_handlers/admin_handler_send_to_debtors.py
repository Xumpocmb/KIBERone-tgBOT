import asyncio
import os

from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.crm_logic.alfa_crm_api import check_client_balance_from_crm
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
    users_in_db = await get_all_users(session)
    debtors_text = """
    Уважаемый клиент! У нас не отобразилась ваша оплата за занятия. Оплатить через ЕРИП можно по ссылке https://clck.ru/36h7Df или оплатить на месте. \nВаш KIBERone!
    """
    await callback.answer()
    await callback.message.answer("Рассылка запущена.. Она будет длиться долгое время.. В конце будет получен отчет.")
    good_send, bad_send = await broadcast_message(bot=bot, users=users_in_db, text=debtors_text)
    await callback.message.answer(f'Рассылка завершена. Сообщение получило <b>{good_send}</b>, '
                         f'НЕ получило <b>{bad_send}</b> пользователей.',
                         reply_markup=admin_main_menu_inline_keyboard)



async def broadcast_message(bot, users, text: str = None):
    good_send = 0
    bad_send = 0
    for user in users:
        if user.tg_id not in admins_list:
            user_branch_ids = list(map(int, user.user_branch_ids))
            user_paid_count = await check_client_balance_from_crm(user.phone_number, user_branch_ids, user.is_study, True)
            if user_paid_count < 0:
                try:
                    chat_id = user.tg_id
                    await bot.send_message(chat_id=chat_id, text=text)
                    good_send += 1
                except Exception as e:
                    logger.error(f"Не удалось отправить сообщение пользователю {user.tg_id} / {user.phone_number}: {e}")
                    bad_send += 1
                finally:
                    await asyncio.sleep(0.5)
    return good_send, bad_send

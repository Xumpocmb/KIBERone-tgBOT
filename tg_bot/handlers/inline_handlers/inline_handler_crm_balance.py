from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from crm_logic.alfa_crm_api import find_user_by_phone
from database.engine import session_maker
from database.orm_query import orm_get_user_by_tg_id
from tg_bot.keyboards.keyboard_start import main_menu_button_keyboard
from tg_bot.middlewares.middleware_database import DataBaseSession

crm_balance_router: Router = Router()
crm_balance_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


@crm_balance_router.callback_query(F.data == 'crm_balance')
async def balance_handler(callback: CallbackQuery, session: AsyncSession):
    user_tg_id = callback.from_user.id
    logger.debug(f"Обработка запроса на получение баланса от пользователя с ID: {user_tg_id}")

    try:
        user_in_db = await orm_get_user_by_tg_id(session, user_tg_id)
        if user_in_db:
            user_phone = user_in_db.phone_number
            user_in_crm = await find_user_by_phone(user_phone)
            if user_in_crm.get("total", 0):
                items = user_in_crm.get("items", [])
                for item in items:
                    user_name = item.get("name", '')
                    user_balance = item.get("balance", 0)
                    user_paid_count = item.get("paid_count", 0)
                    user_paid_till = item.get("paid_till", None)
                    user_next_lesson_date = item.get("next_lesson_date", None)

                    text_message = (
                        f"<b>{user_name}</b>\n"
                        f"Ваш баланс: <b>{user_balance}</b> руб.\n"
                        f"Количество оплаченных занятий: <b>{user_paid_count}</b>\n"
                        f"'Оплачено до: <b>{user_paid_till}</b>'\n"
                    )

                    if user_paid_till:
                        text_message += f"Оплачено до: <b>{user_paid_till}</b>\n"
                    else:
                        text_message += f"Вам необходимо оплатить занятия до: <b>{user_next_lesson_date}</b>\n"

                    await callback.message.answer(text_message, reply_markup=main_menu_button_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на получение баланса от пользователя с ID {user_tg_id}: {e}")
        await callback.message.answer(
            'Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.')
    finally:
        await callback.answer()
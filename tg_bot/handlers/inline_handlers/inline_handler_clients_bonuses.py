from aiogram import F
from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.operators import eq

from tg_bot.database.engine import session_maker
from tg_bot.database.models import Promotion
from logger_config import get_logger
from tg_bot.database.orm_query import orm_get_user_by_tg_id
from tg_bot.keyboards.inline_keyboards.inline_keyboard_clients_bonuses import clients_bonuses_menu_inline, \
    clients_bonuses_menu_inline_for_lead
from tg_bot.keyboards.inline_keyboards.inline_keyboard_promo import make_inline_promo_kb
from tg_bot.middlewares.middleware_database import DataBaseSession

logger = get_logger()

promo_router: Router = Router()
promo_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))




@promo_router.callback_query(F.data == 'clients_bonuses')
async def process_button_clients_bonuses_press(callback: CallbackQuery, session: AsyncSession):
    await callback.message.delete()
    user_id = callback.from_user.id
    try:
        user_from_db = await orm_get_user_by_tg_id(session, user_id)
        if user_from_db.is_study == 1:
            await callback.message.answer(
                text='Наши акции:',
                reply_markup=clients_bonuses_menu_inline
            )
        else:
            await callback.message.answer(
                text='Наши акции:', reply_markup=clients_bonuses_menu_inline_for_lead)
    except TelegramAPIError as e:
        logger.error(f"Ошибка API Telegram при обработке запроса от пользователя с ID {user_id}: {e}")
    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при обработке запроса от пользователя с ID {user_id}: {e}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при обработке запроса от пользователя с ID {user_id}: {e}")
    finally:
        await callback.answer()


# главное меню раздела Promo
@promo_router.callback_query(F.data == 'promo')
async def process_button_promo_press(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    callback_data = callback.data
    logger.debug(f"Получен запрос на акции от пользователя с ID {user_id}. Данные колбэка: {callback_data}")

    try:
        await callback.message.answer(
            text='Наши акции:',
            reply_markup=await make_inline_promo_kb(session)
        )
        logger.debug(f"Отправлено сообщение с акциями пользователю с ID {user_id}.")

        await callback.message.delete()
        logger.debug(f"Исходное сообщение удалено для пользователя с ID {user_id}.")

        await callback.answer()
        logger.debug(f"Подтверждение кнопки отправлено пользователю с ID {user_id}.")

    except TelegramAPIError as e:
        logger.error(f"Ошибка API Telegram при обработке запроса от пользователя с ID {user_id}: {e}")

    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при обработке запроса от пользователя с ID {user_id}: {e}")

    except Exception as e:
        logger.error(f"Неизвестная ошибка при обработке запроса от пользователя с ID {user_id}: {e}")


# пункт раздела наши акции
@promo_router.callback_query(F.data.startswith('promo-'))
async def process_button_promo_question_press(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    logger.debug(f"Получен запрос на акцию от пользователя с ID: {user_id}, данные: {callback.data}")

    try:
        promo_id = int(callback.data.split('-')[1])
        logger.debug(f"Извлечен ID акции: {promo_id}")

        query = select(Promotion).where(eq(Promotion.id, int(callback.data.split('-')[1])))
        result = await session.execute(query)
        promo = result.scalar()

        if promo:
            logger.debug(f"Получен ответ акции для ID {promo_id}: {promo.answer}")

            await callback.message.answer(
                text=promo.answer,
                reply_markup=await make_inline_promo_kb(session)
            )
            logger.info(f"Отправлен ответ на акцию пользователю с ID {user_id}.")
        else:
            logger.warning(f"Акция с ID {promo_id} не найдена.")

        await callback.message.delete()
        logger.debug(f"Исходное сообщение удалено для пользователя с ID {user_id}.")

        await callback.answer()
        logger.debug(f"Обработка запроса на акцию завершена для пользователя с ID {user_id}.")

    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при обработке запроса на акцию от пользователя с ID {user_id}: {e}")
        await callback.message.answer(
            text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.")
        await callback.answer()

    except Exception as e:
        logger.error(f"Неизвестная ошибка при обработке запроса на акцию от пользователя с ID {user_id}: {e}")
        await callback.message.answer(text="Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        await callback.answer()

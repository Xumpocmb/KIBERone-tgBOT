from aiogram import F
from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.database.engine import session_maker
from tg_bot.database.models import Partner
from tg_bot.database.orm_query import orm_get_user_by_tg_id
from logger_config import get_logger
from tg_bot.keyboards.inline_keyboards.inline_back_to_main import back_to_main_inline
from tg_bot.keyboards.inline_keyboards.inline_keyboard_partner import make_inline_partner_kb, \
    make_inline_partner_categories_kb
from tg_bot.middlewares.middleware_database import DataBaseSession
from tg_bot.utils.parthner_clicker_count import increment_click_count

logger = get_logger()

partner_router: Router = Router()
partner_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))






@partner_router.callback_query(F.data == 'lets_study')
async def process_button_lets_study_press(callback: CallbackQuery, session: AsyncSession):
    await callback.message.answer(
        text='Для того, чтобы узнать подробнее Вам необходимо быть нашим клиентом.\n'
             'А если Вы уже заполняли договор на обучение, перезапустите бота через Меню -> /start.',
        reply_markup=back_to_main_inline)
    await callback.answer()


@partner_router.callback_query(F.data.startswith('partners_of_category-'))
async def process_button_partner_category_press(callback: CallbackQuery, session: AsyncSession):
    """Присылает партнеров выбранной категории"""
    user_id = callback.from_user.id
    logger.debug(f"Получен запрос на информацию о партнерах от пользователя с ID: {user_id}")
    callback_data = callback.data
    category_id = int(callback_data.split('-')[1])
    try:
        user_from_db = await orm_get_user_by_tg_id(session, user_id)
        await callback.message.answer(
            text='Список партнеров:',
            reply_markup=await make_inline_partner_kb(session, category_id, is_study=user_from_db.is_study)
        )
        logger.info(f"Информация о партнерах отправлена пользователю с ID {user_id}.")

        await callback.message.delete()
        logger.debug(f"Исходное сообщение удалено для пользователя с ID {user_id}.")

        await callback.answer()
        logger.debug(f"Подтверждение кнопки отправлено пользователю с ID {user_id}.")

    except TelegramAPIError as e:
        logger.error(f"Ошибка API Telegram при обработке запроса партнера от пользователя с ID {user_id}: {e}")
    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при выполнении запроса партнеров для пользователя с ID {user_id}: {e}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при обработке запроса партнера от пользователя с ID {user_id}: {e}")


@partner_router.callback_query(F.data == 'partners_categories')
async def get_partner_categories(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    try:
        await callback.message.answer(text='Выберите категорию:', reply_markup=await make_inline_partner_categories_kb(session))
        await callback.message.delete()
        logger.debug(f"Исходное сообщение удалено для пользователя с ID {user_id}.")
    except TelegramAPIError as e:
        logger.error(f"Ошибка API Telegram при обработке запроса категорий партнеров от пользователя с ID {user_id}: {e}")
    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при выполнении запроса категорий партнеров для пользователя с ID {user_id}: {e}")
    finally:
        await callback.answer()
        logger.debug(f"Подтверждение кнопки отправлено пользователю с ID {user_id}.")




@partner_router.callback_query(F.data.startswith('partner-'))
async def process_button_partner_question_press(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    callback_data = callback.data
    logger.info(
        f"Получен запрос на информацию о партнере от пользователя с ID {user_id}. Данные колбэка: {callback_data}")

    try:
        increment_click_count(callback_data)

        partner_id = int(callback_data.split('-')[1])
        logger.debug(f"Извлечен ID партнера: {partner_id}")

        query = select(Partner).where(Partner.id == partner_id)
        result = await session.execute(query)
        partner = result.scalar()

        if partner:
            logger.debug(f"Получена информация о партнере: {partner.description}")
            await callback.message.answer(text=partner.description, reply_markup=back_to_main_inline)
        else:
            logger.warning(f"Партнер с ID {partner_id} не найден.")
            await callback.message.answer(text="Партнер не найден.")
    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при обработке запроса от пользователя с ID {user_id}: {e}")

    except TelegramAPIError as e:
        logger.error(f"Ошибка API Telegram при обработке запроса от пользователя с ID {user_id}: {e}")

    except Exception as e:
        logger.error(f"Неизвестная ошибка при обработке запроса от пользователя с ID {user_id}: {e}")
    finally:
        await callback.answer()
        logger.debug(f"Подтверждение кнопки отправлено пользователю с ID {user_id}.")


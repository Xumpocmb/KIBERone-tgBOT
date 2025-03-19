from aiogram import F
from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.database.engine import session_maker
from logger_config import get_logger
from tg_bot.filters.filter_admin import check_admin
from tg_bot.handlers.handler_main_menu import get_user_keyboard
from tg_bot.middlewares.middleware_database import DataBaseSession

logger = get_logger()

inline_main_router: Router = Router()
inline_main_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


@inline_main_router.callback_query(F.data == 'inline_main')
async def process_button_inline_back_to_main(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    logger.debug(f"Получен запрос на обработку кнопки 'inline_back_to_main' от пользователя {user_id}")

    is_admin = check_admin(user_id)
    logger.debug(f"Пользователь {user_id} является администратором: {is_admin}")

    if is_admin:
        logger.info(f"Пользователь {user_id} является администратором. Никаких действий не предпринимается.")
    else:
        try:
            user_keyboard = await get_user_keyboard(session, user_id)
            try:
                await callback.message.delete()
            except Exception as e:
                logger.error(f"Не удалось удалить исходное сообщение пользователя {user_id}: {e}")
            await callback.message.answer(
                text='Выберите действие..',
                reply_markup=user_keyboard
            )
            logger.info(f"Отправлено сообщение пользователю {user_id} с клавиатурой.")

            await callback.message.delete()
            logger.info(f"Сообщение удалено у пользователя {user_id}.")

            await callback.answer()
            logger.debug(f"Подтверждение нажатия кнопки отправлено пользователю {user_id}.")
        except Exception as e:
            logger.error(f"Ошибка при обработке кнопки 'inline_back_to_main' для пользователя {user_id}: {e}")


@inline_main_router.callback_query()
async def process_any_button_(callback: CallbackQuery):
    user_id = callback.from_user.id
    callback_data = callback.data

    logger.info(f"Получен запрос от пользователя с ID {user_id}. Данные колбэка: {callback_data}")

    try:
        await callback.message.delete()
        logger.debug(f"Исходное сообщение удалено для пользователя с ID {user_id}.")

        await callback.answer()
        logger.debug(f"Подтверждение кнопки отправлено пользователю с ID {user_id}.")

    except TelegramAPIError as e:
        logger.error(f"Ошибка API Telegram при обработке запроса от пользователя с ID {user_id}: {e}")

    except Exception as e:
        logger.error(f"Неизвестная ошибка при обработке запроса от пользователя с ID {user_id}: {e}")

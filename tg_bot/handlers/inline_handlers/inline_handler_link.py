from aiogram import F
from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery

from logger_config import get_logger
from tg_bot.keyboards.inline_keyboards.inline_keyboard_link import make_inline_link_kb

logger = get_logger()

button_link_router: Router = Router()


@button_link_router.callback_query(F.data == 'link')
async def process_button_link_press(callback: CallbackQuery):
    user_id = callback.from_user.id
    logger.debug(f"Получен запрос на ссылки от пользователя с ID: {user_id}")

    try:
        await callback.message.answer(
            text='Ссылки на наши социальные сети:',
            reply_markup=await make_inline_link_kb()
        )
        logger.info(f"Сообщение со ссылками отправлено пользователю с ID: {user_id}")

        await callback.message.delete()
        logger.debug(f"Исходное сообщение удалено для пользователя с ID: {user_id}")

        await callback.answer()
        logger.debug(f"Обработка запроса на ссылки завершена для пользователя с ID: {user_id}")
    except TelegramAPIError as e:
        logger.error(f"Ошибка Telegram API при обработке запроса от пользователя с ID {user_id}: {e}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при обработке запроса от пользователя с ID {user_id}: {e}")

import asyncio

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import session_maker
from tg_bot.filters.filter_admin import check_admin
from tg_bot.keyboards.keyboard_start import main_menu_button_keyboard
from tg_bot.middlewares.middleware_database import DataBaseSession

from tg_bot.keyboards.inline_keyboards.inline_keyboard_tg_links import make_tg_links_inline_keyboard

logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")
inline_tg_links_router: Router = Router()
inline_tg_links_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


@inline_tg_links_router.callback_query(F.data == 'tg_links')
async def tg_links_handler(callback: CallbackQuery, session: AsyncSession):
    user_tg_id = callback.from_user.id
    logger.debug(f"Обработка запроса на получение ссылок от пользователя с ID: {user_tg_id}")

    try:
        is_admin = check_admin(user_tg_id)
        if is_admin:
            logger.info(f"Пользователь с ID {user_tg_id} является администратором.")
            await callback.message.answer(
                'Администратор не может получать ссылки на телеграм-каналы',
                reply_markup=main_menu_button_keyboard
            )
            logger.debug(f"Отправлено сообщение о запрете получения ссылок администратору с ID {user_tg_id}.")
        else:
            formatted_text = """
                **Канал-общий**: Хотите быть в курсе свежих новостей в мире IT и узнавать новости от KIBERone? Присоединяйтесь к нашей дружной команде и будете на волне!

                **Канал-города**: Чтобы не пропустить акции от KIBERone в вашем городе, быть в курсе всех мероприятий для детей и родителей, не упускать информацию о переносах занятий на каникулах и многое другое, то мы настоятельно рекомендуем вступить в группу и быть в центре событий жизни KIBERone!

                **Чат-группы**: Мы НЕ РЕКОМЕНДУЕМ вступать в этот чат, если вы не хотите быть на связи с вашим тьютором и ассистентом, быть в группе ответственных родителей, кто интересуется успехами детей, то вам точно не нужен этот чат. P.S – все резиденты должны быть в этом чате))
                """
            await callback.message.answer(
                formatted_text,
                reply_markup=await make_tg_links_inline_keyboard(session, user_tg_id)
            )
            logger.debug(f"Отправлены ссылки на телеграм-каналы пользователю с ID {user_tg_id}.")

        await callback.answer()
        logger.debug(f"Обработка запроса на получение ссылок завершена для пользователя с ID {user_tg_id}.")
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на получение ссылок от пользователя с ID {user_tg_id}: {e}")
        await callback.message.answer(
            'Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.'
        )
        await callback.answer()

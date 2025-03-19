from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.database.engine import session_maker
from tg_bot.database.orm_query import orm_get_user_by_tg_id
from logger_config import get_logger
from tg_bot.filters.filter_admin import check_admin
from tg_bot.keyboards.inline_keyboards.inline_keyboard_tg_links import make_tg_links_inline_keyboard
from tg_bot.middlewares.middleware_database import DataBaseSession

logger = get_logger()

inline_tg_links_router: Router = Router()
inline_tg_links_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))

tg_links_message = (
    "\t<b>Канал-общий:</b> Хотите быть в курсе свежих новостей в мире IT и узнавать новости от KIBERone? "
    "Присоединяйтесь к нашей дружной команде и будете на волне!\n"
    "\n\t<b>Канал-города:</b> Чтобы не пропустить акции от KIBERone в вашем городе, "
    "быть в курсе всех мероприятий для детей и родителей, не упускать информацию о переносах занятий "
    "на каникулах и многое другое, то мы настоятельно рекомендуем вступить в группу и "
    "быть в центре событий жизни KIBERone!\n"
    "\n\t<b>Чат-группы:</b> Мы НЕ РЕКОМЕНДУЕМ вступать в этот чат, если вы не хотите быть на связи с вашим "
    "тьютором и ассистентом, быть в группе ответственных родителей, кто интересуется успехами детей, "
    "то вам точно не нужен этот чат. P.S – все резиденты должны быть в этом чате))")


@inline_tg_links_router.callback_query(F.data == 'tg_links')
async def tg_links_handler(callback: CallbackQuery, session: AsyncSession):

    logger.debug(f"Обработка запроса на получение ссылок..")
    user_tg_id = callback.from_user.id
    try:
        user_data_in_db = await orm_get_user_by_tg_id(session, user_tg_id)
        if user_data_in_db is None:
            logger.error(f"Пользователь с ID {user_tg_id} не найден в базе данных.")
            await callback.message.answer(
                'Вы не зарегистрированы в нашем чате. Пожалуйста, зарегистрируйтесь через команду /start')
            await callback.answer()
            return

        is_admin = check_admin(user_tg_id)
        if is_admin:
            logger.info(f"Пользователь с ID {user_tg_id} является администратором.")
            await callback.message.answer(
                'Администратор не может получать ссылки на телеграм-каналы')
            logger.debug(f"Отправлено сообщение о запрете получения ссылок администратору с ID {user_tg_id}.")
        else:
            user_crm_id = user_data_in_db.user_crm_id
            user_branch_ids = user_data_in_db.user_branch_ids
            if user_crm_id is None:
                logger.error(f"ID пользователя {user_tg_id} не найден в CRM.")
                await callback.message.answer(
                    'Вы не зарегистрированы в CRM. Пожалуйста, зарегистрируйтесь через команду /start')
                await callback.answer()
                return

            await callback.message.answer(
                tg_links_message,
                reply_markup=await make_tg_links_inline_keyboard(session, user_tg_id, user_crm_id, user_branch_ids, include_back_button=True)
            )
            logger.debug(f"Отправлены ссылки на телеграм-каналы пользователю с ID {user_tg_id}.")
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на получение ссылок от пользователя с ID {user_tg_id}: {e}")
        await callback.message.answer(
            'Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.'
        )
    finally:
        await callback.answer()
        logger.debug(f"Обработка запроса на получение ссылок завершена для пользователя с ID {user_tg_id}.")

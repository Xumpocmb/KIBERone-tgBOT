from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import session_maker
from tg_bot.middlewares.middleware_database import DataBaseSession

from tg_bot.keyboards.inline_keyboards.inline_keyboard_tg_links import make_tg_links_inline_keyboard

logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")
inline_tg_links_router: Router = Router()
inline_tg_links_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


@inline_tg_links_router.callback_query(F.data == 'tg_links')
async def tg_links_handler(callback: CallbackQuery, session: AsyncSession):
    user_tg_id = callback.from_user.id
    # Добавить проверку на админа. Если админ, то никаких ссылок не показывать
    await callback.message.answer('Ссылки на наши телеграм-каналы:',
                                  reply_markup=await make_tg_links_inline_keyboard(session, user_tg_id))
    await callback.answer()

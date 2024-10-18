import asyncio
import os

from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.database.engine import session_maker
from tg_bot.database.orm_query import get_all_users
from tg_bot.keyboards.inline_keyboards.inline_admin_main_menu import admin_main_menu_inline_keyboard
from tg_bot.middlewares.middleware_database import DataBaseSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv

load_dotenv()

admins_list: list = os.getenv("ADMINS").split(",")


class BroadcastStates(StatesGroup):
    waiting_for_text = State()


admin_send_all_router: Router = Router()
admin_send_all_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


@admin_send_all_router.callback_query((F.from_user.id in admins_list) & (F.data == "admin_send_all"))
async def send_all_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.message.answer("Пожалуйста, введите текст для рассылки\n"
                                  "Для отмены введите 'отмена' (без ковычек):")
    await state.set_state(BroadcastStates.waiting_for_text)
    await callback.answer()


@admin_send_all_router.message(F.content_type.in_({'text', 'photo', 'document', 'video', 'audio'}),
                               BroadcastStates.waiting_for_text)
async def get_broadcast_text(message: Message, state: FSMContext, session: AsyncSession):
    content_type = message.content_type
    bot = message.bot

    if message.text == "отмена":
        await message.answer("Рассылка отменена.")
        await state.clear()
    else:
        users_in_db = await get_all_users(session)
        await message.answer("Рассылка запущена.. Она будет длиться долгое время.. В конце будет получен отчет.")
        good_send, bad_send = await broadcast_message(
            bot=bot,
            users=users_in_db,
            text=message.text if content_type == ContentType.TEXT else None,
            photo_id=message.photo[-1].file_id if content_type == ContentType.PHOTO else None,
            document_id=message.document.file_id if content_type == ContentType.DOCUMENT else None,
            video_id=message.video.file_id if content_type == ContentType.VIDEO else None,
            audio_id=message.audio.file_id if content_type == ContentType.AUDIO else None,
            caption=message.caption,
            content_type=content_type
        )
        await message.answer(f'Рассылка завершена. Сообщение получило <b>{good_send}</b>, '
                             f'НЕ получило <b>{bad_send}</b> пользователей.',
                             reply_markup=admin_main_menu_inline_keyboard)
        await state.clear()


async def broadcast_message(bot, users, text: str = None, photo_id: int = None, document_id: int = None,
                            video_id: int = None, audio_id: int = None, caption: str = None,
                            content_type: str = None):
    good_send = 0
    bad_send = 0
    for user in users:
        try:
            chat_id = user.tg_id
            if content_type == ContentType.TEXT:
                await bot.send_message(chat_id=chat_id, text=text)
            elif content_type == ContentType.PHOTO:
                await bot.send_photo(chat_id=chat_id, photo=photo_id, caption=caption)
            elif content_type == ContentType.DOCUMENT:
                await bot.send_document(chat_id=chat_id, document=document_id, caption=caption)
            elif content_type == ContentType.VIDEO:
                await bot.send_video(chat_id=chat_id, video=video_id, caption=caption)
            elif content_type == ContentType.AUDIO:
                await bot.send_audio(chat_id=chat_id, audio=audio_id, caption=caption)
            good_send += 1
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {user.tg_id} / {user.phone_number}: {e}")
            bad_send += 1
        finally:
            await asyncio.sleep(1)

    return good_send, bad_send

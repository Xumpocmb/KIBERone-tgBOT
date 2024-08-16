from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery

from loguru import logger

from tg_bot.keyboards.inline_keyboards.inline_keyboard_main_menu import main_menu_inline_keyboard

inline_main_router: Router = Router()


# присылает главное inline меню
@inline_main_router.callback_query(F.data == 'inline_main')
async def process_button_inline_back_to_main(callback: CallbackQuery):
    await callback.message.answer(text='Выберите действие..',
                                  reply_markup=main_menu_inline_keyboard)
    await callback.message.delete()
    await callback.answer()


# отвечает на любой call-back для теста
@inline_main_router.callback_query()
async def process_any_button_(callback: CallbackQuery):
    logger.info(f'Callback: {callback.data}')
    await callback.message.delete()
    await callback.answer()

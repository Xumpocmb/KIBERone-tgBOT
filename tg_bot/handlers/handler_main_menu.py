from aiogram import Router, F
from aiogram.types import Message
from loguru import logger

from tg_bot.keyboards.inline_keyboards.inline_keyboard_main_menu import main_menu_inline_keyboard

logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")
main_menu_router: Router = Router()


@main_menu_router.message(F.text == 'Главное меню')
async def main_menu_handler(message: Message):
    logger.debug('Главное меню')
    await message.answer('Главное меню', reply_markup=main_menu_inline_keyboard)

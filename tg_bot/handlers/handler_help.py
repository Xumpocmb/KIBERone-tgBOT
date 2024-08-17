from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from tg_bot.keyboards.keyboard_start import main_menu_button_keyboard

command_help_router: Router = Router()


@command_help_router.message(Command("help"))
async def help_handler(message: Message):
    formatted_text = """
    Наш бот создан помогать Вам в получении информации. Для того, чтобы информацию получить,
    бот отправляет запросы на наши сервера, и иногда Вам может показаться что он завис.
    Обратите внимание, что когда бот работает над Вашим запросом, он использует действие "набирает текст".
    Если бот прекратил набирать текст, а ответа нету - попробуйте повторить запрос.
    Такое бывает, во время сильной нагрузки на наши сервера.
    
    <b>Команды нашего бота:</b>
    <code>/start</code> - Начать работу с ботом/перезапуск бота
    <code>/menu</code> - Вызов главного меню бота
    <code>/help</code> - Помощь
    """
    await message.answer(formatted_text, reply_markup=main_menu_button_keyboard)

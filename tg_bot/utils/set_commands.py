from aiogram import Bot
from aiogram.types import BotCommand


async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command='/start',
                   description='Начало работы/Перезапуск'),
        BotCommand(command='/menu',
                   description='Главное меню'),
    ]
    await bot.set_my_commands(main_menu_commands)
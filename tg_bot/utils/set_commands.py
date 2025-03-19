from aiogram import Bot
from aiogram.types import BotCommand


async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command='/menu',
                   description='КИБЕР меню'),
        BotCommand(command='/start',
                   description='Перезапуск'),
    ]
    try:
        await bot.set_my_commands(main_menu_commands)
        print("Commands set")
    except Exception:
        print("Commands not set")

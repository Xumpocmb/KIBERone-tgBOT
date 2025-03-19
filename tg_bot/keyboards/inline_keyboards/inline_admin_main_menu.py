import os

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

button_1: InlineKeyboardButton = InlineKeyboardButton(
    text="Создать рассылку", callback_data="admin_send_all")

button_2: InlineKeyboardButton = InlineKeyboardButton(
    text="Список пользователей", callback_data="admin_user_list")

button_3: InlineKeyboardButton = InlineKeyboardButton(
    text="Список задач", callback_data="tasks_list")

button_4: InlineKeyboardButton = InlineKeyboardButton(
    text="Статистика по партнерам", callback_data="parthner_statistic")

button_5: InlineKeyboardButton = InlineKeyboardButton(
    text="Админ панель", web_app=WebAppInfo(url=f"https://{os.getenv('NGROK') if os.getenv('DEBUG_WEB_APP') == 'True' else os.getenv('DOMAIN')}/admin"))

button_6: InlineKeyboardButton = InlineKeyboardButton(
    text="Админ панель2", web_app=WebAppInfo(url=f"https://{os.getenv('NGROK') if os.getenv('DEBUG_WEB_APP') == 'True' else os.getenv('DOMAIN')}/admin_management/index_admin"))

button_7: InlineKeyboardButton = InlineKeyboardButton(
    text="Рассылка должникам", callback_data="admin_send_to_debtors")

admin_main_menu_inline_keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(
    inline_keyboard=[
        [button_1],
        [button_2],
        [button_3],
        [button_4],
        [button_5],
        [button_6],
        [button_7],
    ]
)

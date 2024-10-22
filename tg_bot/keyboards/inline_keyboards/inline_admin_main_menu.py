from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

button_1: InlineKeyboardButton = InlineKeyboardButton(
    text="Создать рассылку", callback_data="admin_send_all"
)

button_2: InlineKeyboardButton = InlineKeyboardButton(
    text="Список пользователей", callback_data="admin_user_list"
)

button_3: InlineKeyboardButton = InlineKeyboardButton(
    text="Список задач", callback_data="tasks_list"
)

button_4: InlineKeyboardButton = InlineKeyboardButton(
    text="Статистика по партнерам", callback_data="parthner_statistic"
)

button_5: InlineKeyboardButton = InlineKeyboardButton(
    text="Резюме", web_app=WebAppInfo(url="https://kiberonetgbot.online/kiberclub/resume/")
)

admin_main_menu_inline_keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(
    inline_keyboard=[
        [button_1],
        [button_2],
        [button_3],
        [button_4],
        [button_5],
    ]
)

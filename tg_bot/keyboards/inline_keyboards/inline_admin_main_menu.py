from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

button_1: InlineKeyboardButton = InlineKeyboardButton(
    text="Создать рассылку", callback_data="admin_send_all"
)

button_2: InlineKeyboardButton = InlineKeyboardButton(
    text="Список пользователей в БД", callback_data="admin_user_list"
)

button_3: InlineKeyboardButton = InlineKeyboardButton(
    text="Список пользователей в БД", callback_data="tasks_list"
)

admin_main_menu_inline_keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(
    inline_keyboard=[
        [button_1],
        [button_2],
        [button_3],
    ]
)

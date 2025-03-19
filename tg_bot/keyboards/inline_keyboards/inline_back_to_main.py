from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

button_1: InlineKeyboardButton = InlineKeyboardButton(
    text='<< Главное меню',
    callback_data='inline_main')


# Создаем объект inline-клавиатуры
back_to_main_inline: InlineKeyboardMarkup = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            button_1
        ],
    ]
)

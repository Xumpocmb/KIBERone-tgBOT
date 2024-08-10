from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

button_1: KeyboardButton = KeyboardButton(text='Главное меню')

main_menu_button_keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
    keyboard=[
        [button_1,]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder='Выберите действие..',
)

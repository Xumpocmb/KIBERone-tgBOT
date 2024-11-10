from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

button_1: InlineKeyboardButton = InlineKeyboardButton(
    text='Партнеры KIBERone',
    callback_data='partners_categories')

button_2: InlineKeyboardButton = InlineKeyboardButton(
    text='Скидки на обучение',
    callback_data='promo')

button_3: InlineKeyboardButton = InlineKeyboardButton(
    text='Платформа Lim English',
    callback_data='english_platform')

button_4: InlineKeyboardButton = InlineKeyboardButton(
    text='<< Главное меню',
    callback_data='inline_main')


clients_bonuses_menu_inline: InlineKeyboardMarkup = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            button_1
        ],[
            button_2
        ],[
            button_3
        ],
    ]
)


clients_bonuses_menu_inline_for_lead: InlineKeyboardMarkup = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            button_1
        ],[
            button_2
        ],
    ]
)
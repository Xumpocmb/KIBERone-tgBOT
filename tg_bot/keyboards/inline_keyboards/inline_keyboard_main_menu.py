from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

button_1: InlineKeyboardButton = InlineKeyboardButton(
    text='Часто задаваемые вопросы',
    callback_data='FAQ')

button_2: InlineKeyboardButton = InlineKeyboardButton(
    text='Оплата по ЕРИП',
    callback_data='oplata_erip')

button_3: InlineKeyboardButton = InlineKeyboardButton(
    text='Назначить отработку',
    callback_data='contact')

button_4: InlineKeyboardButton = InlineKeyboardButton(
    text='Платформа английского Lim English',
    callback_data='english_platform')

button_5: InlineKeyboardButton = InlineKeyboardButton(
    text='Наши АКЦИИ для резидентов',
    callback_data='promo')

button_6: InlineKeyboardButton = InlineKeyboardButton(
    text='Наши Партнёры',
    callback_data='partner')

button_7: InlineKeyboardButton = InlineKeyboardButton(
    text='Контакт Менеджера',
    callback_data='contact')

button_8: InlineKeyboardButton = InlineKeyboardButton(
    text='Социальные сети',
    callback_data='link')

button_9: InlineKeyboardButton = InlineKeyboardButton(
    text='Ссылки на телеграм чаты',
    callback_data='tg_links')

# Создаем объект inline-клавиатуры
main_menu_inline_keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            button_1
        ],
        [
            button_2
        ],
        [
            button_3
        ],
        [
            button_4
        ],
        [
            button_5
        ],
        [
            button_6
        ],
        [
            button_7
        ],
        [
            button_8
        ],
        [
            button_9
        ],
    ]
)

import os

from dotenv import load_dotenv

from tg_kiberclub.settings import BASE_DIR

load_dotenv(os.path.join(BASE_DIR, '.env'))

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

button_1: InlineKeyboardButton = InlineKeyboardButton(
    text='Вопрос & Ответ',
    callback_data='FAQ')

button_2: InlineKeyboardButton = InlineKeyboardButton(
    text='Оплатить',
    callback_data='erip_payment-service')

button_4: InlineKeyboardButton = InlineKeyboardButton(
    text='Платформа английского Lim English',
    callback_data='english_platform')

button_5: InlineKeyboardButton = InlineKeyboardButton(
    text='Бонусы для клиентов',
    callback_data='clients_bonuses')

button_6: InlineKeyboardButton = InlineKeyboardButton(
    text='Наши Партнёры',
    callback_data='partners_list')

button_7: InlineKeyboardButton = InlineKeyboardButton(
    text='Ваш менеджер KIBERone',
    callback_data='contact_manager')

button_8: InlineKeyboardButton = InlineKeyboardButton(
    text='Будь в тренде! (Inst, Tg)',
    callback_data='links_menu')

button_9: InlineKeyboardButton = InlineKeyboardButton(
    text='Ссылки на телеграм чаты',
    callback_data='tg_links')

button_10: InlineKeyboardButton = InlineKeyboardButton(
    text='Наши Партнёры',
    callback_data='partner_without_promocodes')

button_11: InlineKeyboardButton = InlineKeyboardButton(
    text='Контакт Менеджера',
    callback_data='lead_contact_manager_lead')

button_12: InlineKeyboardButton = InlineKeyboardButton(
    text='Расписание занятий',
    callback_data='user_scheduler')

button_13: InlineKeyboardButton = InlineKeyboardButton(
    text='Дата пробного занятия',
    callback_data='user_trial_date')

button_14: InlineKeyboardButton = InlineKeyboardButton(
    text='Главный новостной канал KIBERone',
    url='https://t.me/kiberone_bel')

button_15: InlineKeyboardButton = InlineKeyboardButton(
    text='Баланс',
    callback_data='crm_balance')

button_16: InlineKeyboardButton = InlineKeyboardButton(
    text='Личный кабинет KIBERhub',
    web_app=WebAppInfo(url=f"https://{os.getenv('NGROK') if os.getenv('DEBUG_WEB_APP') == 'True' else os.getenv('DOMAIN')}/kiberclub/index/"))

button_17: InlineKeyboardButton = InlineKeyboardButton(
    text='Оплатить через ЕРИП',
    callback_data='erip_payment')

main_menu_inline_keyboard_for_client: InlineKeyboardMarkup = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            button_16
        ],
        [
            button_15, button_2
        ],
        [
            button_5
        ],
        [
            button_7
        ],
        [
            button_8
        ],
        [
            button_1
        ],
    ]
)

main_menu_inline_keyboard_for_lead_with_group: InlineKeyboardMarkup = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            button_15, button_2
        ],
        [
            button_5
        ],
        [
            button_7
        ],
        [
            button_8
        ],
        [
            button_1
        ],
    ]
)

main_menu_inline_keyboard_for_lead_without_group: InlineKeyboardMarkup = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            button_1
        ],
        [
            button_17
        ],
        [
            button_5
        ],
        [
            button_11
        ],
        [
            button_8
        ],
        [
            button_13
        ],
        [
            button_14
        ],
    ]
)

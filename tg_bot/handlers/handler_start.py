import asyncio

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_add_user, orm_get_user, orm_update_user
from tg_bot.filters.filter_admin import check_admin
from tg_bot.handlers.handler_alfacrm import create_lid_alfacrm, check_client_exists
from tg_bot.keyboards.keyboard_contact import contact_keyboard
from tg_bot.keyboards.keyboard_start import start_keyboard

logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")
start_router: Router = Router()


async def handle_existing_user(message: Message, session: AsyncSession, is_admin: bool):
    user_data = {
        'tg_id': message.from_user.id,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'username': message.from_user.username,
    }
    try:
        await orm_update_user(session, user_data=user_data)
    except Exception as e:
        logger.error(e)

    await asyncio.sleep(2)
    greeting = f'Привет, {"администратор " if is_admin else ""}{message.from_user.username}!'
    await message.answer(greeting, reply_markup=start_keyboard)


async def handle_new_user(message: Message, is_admin: bool):
    formatted_message = """
    <b>Предупреждение о сборе информации и обработке персональных данных</b>\n
    Дорогой пользователь! При использовании нашего бота, учтите следующее:
    1. <b>Сбор информации</b>: Мы можем собирать определенные данные о вас, такие как ваш ID пользователя, имя, фамилию, номер телефона (если вы поделились контактом) и другие данные, необходимые для функционирования бота.
    2. <b>Обработка персональных данных</b>: Ваши персональные данные будут использоваться только в рамках функциональности бота. Мы не передаем их третьим лицам и не используем для рекламных целей.
    3. <b>Информационная безопасность</b>: Мы прилагаем все усилия для обеспечения безопасности ваших данных. Однако, помните, что интернет не всегда безопасен, и мы не можем гарантировать абсолютную защиту.
    4. <b>Согласие</b>: Используя нашего бота, вы соглашаетесь с нашей политикой конфиденциальности и обработкой данных.

    <b>Нажмите кнопку "Поделиться контактом", чтобы отправить свой контакт.</b>

    <b>С уважением, KIBERone!</b>
    """
    await asyncio.sleep(2)
    greeting = f'Привет, {"администратор " if is_admin else ""}{message.from_user.username}!\n{formatted_message}'
    await message.answer(greeting, reply_markup=contact_keyboard)


@start_router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession):
    is_admin = check_admin(message.from_user.id)
    user = await orm_get_user(session, tg_id=message.from_user.id)
    if user:
        await handle_existing_user(message, session, is_admin)
    else:
        await handle_new_user(message, is_admin)


@start_router.message(F.contact)
async def handle_contact(message: Message, session: AsyncSession):
    user_data = {
        'tg_id': message.contact.user_id,
        'first_name': message.contact.first_name,
        'last_name': message.contact.last_name,
        'username': message.from_user.username,
        'phone_number': str(message.contact.phone_number)
    }
    try:
        logger.info("Получен контакт. Работаю с данными..")
        await message.answer('Ваш контакт получен.\nИдет обработка данных.. \nОжидайте, это не займет много времени :)')
        await orm_add_user(session, data=user_data)
        await asyncio.sleep(2)
        find_client = await check_client_exists(user_data.get('phone_number', ''))
        if find_client:
            logger.info(f"Клиент с номером {user_data.get('phone_number', '')} найден.")
        else:
            logger.info(f"Клиент с номером {user_data.get('phone_number', '')} не найден.")
            logger.info("Создание нового клиента/лида")
            await create_lid_alfacrm(user_data)
    except Exception as e:
        logger.error(e)
    async with ChatActionSender(bot=message.bot, chat_id=message.chat.id):
        await asyncio.sleep(2)
        await message.answer('Спасибо! Ваш контакт сохранен.', reply_markup=start_keyboard)


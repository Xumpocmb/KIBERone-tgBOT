import asyncio

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, Contact
from aiogram.utils.chat_action import ChatActionSender

from database.orm_query import orm_add_user, orm_get_user, orm_update_user
from keyboards.keyboard_contact import contact_keyboard
from keyboards.keyboard_start import start_keyboard
from tg_bot.bot_logger import logger
from tg_bot.filters.filter_admin import AdminFilter

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.engine import session_maker

start_router: Router = Router()


@start_router.message(AdminFilter, CommandStart())
async def start_handler(message: Message, session: AsyncSession):
    user = await orm_get_user(session, tg_id=message.from_user.id)
    if user:
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
        await orm_update_user(session, user_data=user_data)
        async with ChatActionSender(bot=message.bot, chat_id=message.chat.id):
            await asyncio.sleep(2)
            await message.answer(f'Привет, администратор {message.from_user.username}!',
                                 reply_markup=start_keyboard)
    else:
        async with ChatActionSender(bot=message.bot, chat_id=message.chat.id):
            formatted_message = """
                <b>Предупреждение о сборе информации и обработке персональных данных!</b>\n
                Дорогой пользователь! При использовании нашего бота, учтите следующее:
                1. <b>Сбор информации</b>: Мы можем собирать определенные данные о вас, такие как ваш ID пользователя, имя, фамилию, номер телефона (если вы поделились контактом) и другие данные, необходимые для функционирования бота.
                2. <b>Обработка персональных данных</b>: Ваши персональные данные будут использоваться только в рамках функциональности бота. Мы не передаем их третьим лицам и не используем для рекламных целей.
                3. <b>Информационная безопасность</b>: Мы прилагаем все усилия для обеспечения безопасности ваших данных. Однако, помните, что интернет не всегда безопасен, и мы не можем гарантировать абсолютную защиту.
                4. <b>Согласие</b>: Используя нашего бота, вы соглашаетесь с нашей политикой конфиденциальности и обработкой данных.

                Нажмите кнопку "Поделиться контактом", чтобы отправить свой контакт.

                <b>С уважением, KIBERone!</b>
                """
            await asyncio.sleep(2)
            await message.answer(f'Привет, администратор {message.from_user.username}!\n{formatted_message}',
                                 reply_markup=contact_keyboard)


@start_router.message(Command('start'))
async def start_handler(message: Message):
    async with ChatActionSender(bot=message.bot, chat_id=message.chat.id):
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
        await message.answer(f'Привет, {message.from_user.username}!\n{formatted_message}',
                             reply_markup=contact_keyboard)


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
        logger.info(user_data)
        await orm_add_user(session, data=user_data)
    except Exception as e:
        logger.error(e)
    async with ChatActionSender(bot=message.bot, chat_id=message.chat.id):
        await asyncio.sleep(2)
        await message.answer('Спасибо! Ваш контакт сохранен.')

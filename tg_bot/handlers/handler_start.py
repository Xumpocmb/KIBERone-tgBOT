import asyncio
import json

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_add_user, orm_get_user, orm_update_user
from tg_bot.filters.filter_admin import check_admin
from crm_logic.alfa_crm_api import create_user_in_alfa_crm, find_user_by_phone, get_client_lessons
from tg_bot.keyboards.inline_keyboards.inline_keyboard_tg_links import make_tg_links_inline_keyboard, \
    make_tg_links_inline_keyboard_without_back
from tg_bot.keyboards.keyboard_send_contact import contact_keyboard
from tg_bot.keyboards.keyboard_start import main_menu_button_keyboard

logger.add(
    "debug.log",
    format="{time} {level} {message}",
    level="ERROR",
    rotation="1 MB",
    compression="zip",
)
start_router: Router = Router()


greeting_message = ("Вас приветствует Международная КиберШкола программирования KIBERone!\n"
                    "Если вы зашли в этот чат-бот, то мы уверены, что вы заинтересованы в будущем вашего ребенка и знаете, что изучать программирование сегодня –это даже уже не модно, а НУЖНО! И Вы на правильном пути, ведь мы точно знаем, чему учить детей, чтобы это было актуально через 20 лет!\n"
                    "Мы уже получили ваш контакт, и наши лучшие менеджеры уже спорят, кто первый Вам позвонит!\n"
                    "Но, вы можете сами нам позвонить по номеру +375(29)633-27-79 и уточнить все интересующие вопросы о KIBERone.")

tg_links_message = ("Канал-общий**: Хотите быть в курсе свежих новостей в мире IT и узнавать новости от KIBERone? "
                    "Присоединяйтесь к нашей дружной команде и будете на волне!\n"
                    "Канал-города**: Чтобы не пропустить акции от KIBERone в вашем городе, "
                    "быть в курсе всех мероприятий для детей и родителей, не упускать информацию о переносах занятий "
                    "на каникулах и многое другое, то мы настоятельно рекомендуем вступить в группу и "
                    "быть в центре событий жизни KIBERone!\n"
                    "Чат-группы**: Мы НЕ РЕКОМЕНДУЕМ вступать в этот чат, если вы не хотите быть на связи с вашим "
                    "тьютором и ассистентом, быть в группе ответственных родителей, кто интересуется успехами детей, "
                    "то вам точно не нужен этот чат. P.S – все резиденты должны быть в этом чате))")

async def handle_existing_user(message: Message, session: AsyncSession, is_admin: bool):
    user_data = {
        "tg_id": message.from_user.id,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "username": message.from_user.username,
    }
    try:
        logger.debug("Обновление данных пользователя в БД..")
        await orm_update_user(session, user_data=user_data)
        user = await orm_get_user(session, tg_id=message.from_user.id)
        user_phone = user.get("phone_number")
        crm_client = await find_user_by_phone(user_phone)
        if crm_client:
            await process_existing_user(crm_client, session, message, user_data)
        logger.debug("Данные пользователя обновлены в БД.")
    except Exception as e:
        logger.error(e)
    if is_admin:
        greeting = f'Привет, {"администратор " if is_admin else ""}{message.from_user.username}!'
    else:
        greeting = f'Привет, {message.from_user.username}!'
    await message.answer(greeting, reply_markup=main_menu_button_keyboard)


async def handle_new_user(message: Message):
    formatted_message = """
        Вас приветствует Международная КиберШкола программирования для детей от 6 до 14 лет  KIBERone! 
        Мы точно знаем, чему учить детей, чтобы это было актуально через 20 лет!
        ✅ Цифровая грамотность: Основы программирования, управление данными, работа с нейросетями и искусственным интеллектом;
        ✅ Финансовая грамотность: управление личными финансами;
        ✅ Критическое мышление и решение проблем: умение анализировать информацию и находить решения сложных задач;
        ✅ Эмоциональный интеллект: навыки общения, управление эмоциями и работа в команде.
        
        <b>Предупреждение о сборе информации и обработке персональных данных</b>\n
        
        Дорогой пользователь! При использовании нашего бота, учтите следующее:
        1. <b>Сбор информации</b>: Мы можем собирать определенные данные о вас, такие как ваш ID пользователя, имя, фамилию, номер телефона (если вы поделились контактом) и другие данные, необходимые для функционирования бота.
        2. <b>Обработка персональных данных</b>: Ваши персональные данные будут использоваться только в рамках функциональности бота. Мы не передаем их третьим лицам и не используем для рекламных целей.
        3. <b>Информационная безопасность</b>: Мы прилагаем все усилия для обеспечения безопасности ваших данных. Однако, помните, что интернет не всегда безопасен, и мы не можем гарантировать абсолютную защиту.
        4. <b>Согласие</b>: Используя нашего бота, вы соглашаетесь с нашей политикой конфиденциальности и обработкой данных.

        <b>Нажмите кнопку "Поделиться контактом", чтобы отправить свой контакт.</b>

        <b>С уважением, KIBERone!</b>
        """
    greeting = f"Привет, {message.from_user.username}!\n{formatted_message}"
    logger.debug("Запрашиваю у пользователя контакт..")
    await message.answer(greeting, reply_markup=contact_keyboard)


@start_router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession):
    is_admin = check_admin(message.from_user.id)
    logger.debug("Проверка пользователя в БД..")
    user = await orm_get_user(session, tg_id=message.from_user.id)
    if user:
        logger.debug("Пользователь найден в БД")
        await handle_existing_user(message, session, is_admin)
    else:
        logger.debug("Пользователь не найден в БД")
        await handle_new_user(message)


@start_router.message(F.contact)
async def handle_contact(message: Message, session: AsyncSession):
    try:
        logger.debug("Получен контакт. Обрабатываю данные...")
        user_data = {
            "tg_id": message.contact.user_id,
            "first_name": message.contact.first_name,
            "last_name": message.contact.last_name,
            "username": message.from_user.username,
            "phone_number": str(message.contact.phone_number),
        }

        await message.answer("Ваш контакт получен. Идет обработка данных...")

        if check_admin(message.from_user.id):
            await save_user_data(session, user_data)
            return await message.answer("Спасибо! Ваш контакт сохранен.", reply_markup=main_menu_button_keyboard)

        crm_client = await find_user_by_phone(user_data["phone_number"])
        if crm_client:
            await process_existing_user(crm_client, session, message, user_data)
        else:
            await create_new_user_in_crm(user_data, session, message)

    except Exception as e:
        logger.exception("Произошла ошибка при обработке контакта.")
        await message.answer("Произошла ошибка при обработке вашего контакта. Попробуйте позже.")


async def save_user_data(session, user_data):
    logger.debug("Сохраняю данные пользователя в БД.")
    await orm_add_user(session, data=user_data)


async def process_existing_user(crm_client, session, message, user_data):
    logger.debug(f"Пользователь с номером {user_data['phone_number']} найден в ЦРМ.")
    user_info = crm_client.get("items", [])[0]
    user_data.update({
        "customer_data": json.dumps(crm_client),
        "user_crm_id": user_info.get("id"),
        "is_study": user_info.get("is_study"),
        "user_branch_ids": ','.join(map(str, user_info.get("branch_ids", []))),
    })

    user_lessons = await get_client_lessons(user_data["user_crm_id"], user_info.get("branch_ids", []))
    user_data["user_lessons"] = user_lessons.get("total", 0) > 0

    await save_user_data(session, user_data)

    if user_data["user_lessons"]:
        await send_lesson_links(message, session, user_data["tg_id"])
    else:
        await message.answer("Спасибо! Ваш контакт сохранен.", reply_markup=main_menu_button_keyboard)


async def send_lesson_links(message, session, user_id):
    logger.debug("Отправка ссылок на уроки.")
    await message.answer("Подготавливаем ссылки... Ожидайте!")
    await message.answer(
        tg_links_message,
        reply_markup=await make_tg_links_inline_keyboard_without_back(session, user_id)
    )
    await message.answer("Спасибо! Ваш контакт сохранен.", reply_markup=main_menu_button_keyboard)


async def create_new_user_in_crm(user_data, session, message):
    logger.debug(f"Создание нового пользователя с номером {user_data['phone_number']} в ЦРМ.")
    response = await create_user_in_alfa_crm(user_data)

    new_user_info = response.get("model", {})
    user_data.update({
        "user_crm_id": new_user_info.get("id", -1),
        "user_branch_ids": ','.join(map(str, new_user_info.get("branch_ids", []))),
        "user_lessons": False,
        "is_study": 0,
        "customer_data": json.dumps(new_user_info)
    })

    await save_user_data(session, user_data)
    await message.answer(greeting_message, reply_markup=main_menu_button_keyboard)


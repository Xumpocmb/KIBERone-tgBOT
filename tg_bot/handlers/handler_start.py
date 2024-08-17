import asyncio

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
    user_data = {
        "tg_id": message.contact.user_id,
        "first_name": message.contact.first_name,
        "last_name": message.contact.last_name,
        "username": message.from_user.username,
        "phone_number": str(message.contact.phone_number),
    }
    try:
        logger.debug("Получен контакт. Работаю с данными..")
        await message.answer("Ваш контакт получен.\nИдет обработка данных.. \nОжидайте, мы немножко поколдуем, чтобы подготовить всё для Вас :)")

        is_admin = check_admin(message.from_user.id)
        if is_admin:
            logger.debug("Пользователь является администратором.")
            await orm_add_user(session, data=user_data)
            await message.answer("Спасибо! Ваш контакт сохранен.", reply_markup=main_menu_button_keyboard)
        else:
            find_client = await find_user_by_phone(user_data.get("phone_number", ""))
            if find_client:
                logger.debug(f"Пользователь с номером {user_data.get('phone_number', '')} в ЦРМ уже существует.")

                user_branch_ids: list = find_client.get("items", [])[0].get("branch_ids", [])
                is_study = find_client.get("items", [])[0].get("is_study")
                user_crm_id: int = find_client.get("items", [])[0].get("id", None)

                logger.debug(f"Проверяю, есть ли у пользователя уроки в ЦРМ..")
                user_lessons = await get_client_lessons(user_crm_id, user_branch_ids)

                user_data ["user_crm_id"] = user_crm_id
                user_data["is_study"] = is_study
                user_data["user_branch_ids"] = ','.join(map(str, user_branch_ids))
                user_data["user_lessons"] = True if user_lessons else False

                logger.debug(f"Заношу данные пользователя в свою БД..")
                await orm_add_user(session, data=user_data)
                if find_client.get("items", [])[0].get("is_study") == 1:
                    logger.debug("Пользователь в ЦРМ есть и он обучался. Подготовка ссылок и отправка..")
                    await message.answer("Сейчас мы немножко поколдуем.. Ожидайте!")
                    await message.answer("Ссылки на наши телеграм-каналы:\nПрисоединитесь к ним, пожалуйста!",
                                         reply_markup=await make_tg_links_inline_keyboard_without_back(session,
                                                                                          message.contact.user_id))
                else:
                    logger.debug("Пользователь в ЦРМ есть, но он не обучался")
            else:
                logger.info(f"Пользователь с номером {user_data.get('phone_number', '')} в црм не найден.")
                logger.info("Создание новой карточки в ЦРМ..")
                response = await create_user_in_alfa_crm(user_data)
                logger.debug("Получаю branch_ids в ответе от ЦРМ..")
                user_branch_ids: list = response.get("model", {}).get("branch_ids", [])
                logger.debug("user_branch_ids:", user_branch_ids)
                user_crm_id: int = response.get("model", {}).get("id", -1)
                logger.debug("user_crm_id:", user_crm_id)
                user_data["user_branch_ids"] = ','.join(map(str, user_branch_ids))
                user_data["user_crm_id"] = user_crm_id
                user_data["user_lessons"] = False
                user_data["is_study"] = 0
                logger.debug("Заношу данные пользователя в свою БД..", user_data)
                await orm_add_user(session, data=user_data)
                formatted_text = """
                Вас приветствует Международная КиберШкола программирования KIBERone! 
            Если вы зашли в этот чат-бот, то мы уверены, что вы заинтересованы в будущем вашего ребенка и знаете, что изучать программирование сегодня –это даже уже не модно, а НУЖНО! И Вы на правильном пути, ведь мы точно знаем, чему учить детей, чтобы это было актуально через 20 лет
            Мы уже получили ваш контакт, и наши лучшие менеджеры уже спорят, кто первый Вам позвонит!
            Но, вы можете сами нам позвонить по номеру +375(29)633-27-79 и уточнить все интересующие вопросы о KIBERone.
                """
                await message.answer(formatted_text, reply_markup=main_menu_button_keyboard)
    except Exception as e:
        logger.exception("Произошла ошибка при обработке контакта.")


import asyncio
import json
from sqlite3 import IntegrityError, OperationalError

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from sqlalchemy.exc import IntegrityError, OperationalError
from asyncio import TimeoutError

from database.orm_query import orm_add_user, orm_get_user_by_tg_id, orm_update_user
from tg_bot.filters.filter_admin import check_admin
from crm_logic.alfa_crm_api import (
    create_user_in_alfa_crm,
    find_user_by_phone,
    get_client_lessons,
)
from tg_bot.keyboards.inline_keyboards.inline_keyboard_tg_links import (
    make_tg_links_inline_keyboard,
)
from tg_bot.keyboards.keyboard_send_contact import contact_keyboard
from tg_bot.keyboards.keyboard_start import main_menu_button_keyboard


start_router: Router = Router()


greeting_message = (
    "Вас приветствует Международная КиберШкола программирования KIBERone!\n"
    "Если вы зашли в этот чат-бот, то мы уверены, что вы заинтересованы в будущем вашего ребенка и знаете, что изучать программирование сегодня –это даже уже не модно, а НУЖНО! И Вы на правильном пути, ведь мы точно знаем, чему учить детей, чтобы это было актуально через 20 лет!\n"
    "Мы уже получили ваш контакт, и наши лучшие менеджеры уже спорят, кто первый Вам позвонит!\n"
    "Но, вы можете сами нам позвонить по номеру +375(29)633-27-79 и уточнить все интересующие вопросы о KIBERone."
)

tg_links_message = (
    "\t<b>Канал-общий:</b> Хотите быть в курсе свежих новостей в мире IT и узнавать новости от KIBERone? "
    "Присоединяйтесь к нашей дружной команде и будете на волне!\n"
    "\n\t<b>Канал-города:</b> Чтобы не пропустить акции от KIBERone в вашем городе, "
    "быть в курсе всех мероприятий для детей и родителей, не упускать информацию о переносах занятий "
    "на каникулах и многое другое, то мы настоятельно рекомендуем вступить в группу и "
    "быть в центре событий жизни KIBERone!\n"
    "\n\t<b>Чат-группы:</b> Мы НЕ РЕКОМЕНДУЕМ вступать в этот чат, если вы не хотите быть на связи с вашим "
    "тьютором и ассистентом, быть в группе ответственных родителей, кто интересуется успехами детей, "
    "то вам точно не нужен этот чат. P.S – все резиденты должны быть в этом чате))"
)


async def get_best_items(crm_client):
    try:
        logger.debug("Начало поиска лучших элементов для клиента.")

        # Проверка на наличие элементов у клиента
        items = crm_client.get("items", [])
        if not items:
            logger.info("У клиента отсутствуют элементы.")
            return None

        # Перебор элементов и попытка найти лучший
        for item in items:
            item_id = item.get("id")
            branch_ids = item.get("branch_ids", [])
            is_study = item.get("is_study", 0)

            logger.debug(
                f"Обрабатываю элемент с ID: {item_id}, branch_ids: {branch_ids}, is_study: {is_study}"
            )

            # Получение уроков для клиента по элементу
            try:
                user_lessons = await get_client_lessons(item_id, branch_ids)
            except Exception as e:
                logger.exception(
                    f"Ошибка при получении уроков для элемента {item_id}: {e}"
                )
                continue  # Пропускаем этот элемент и идем к следующему

            # Проверка, является ли элемент обучающим
            if is_study == 1:
                logger.info(f"Найден элемент с обучением (is_study = 1): {item_id}")
                return item
            # Проверка, есть ли уроки у пользователя по элементу
            elif user_lessons.get("total", 0) > 0:
                logger.info(f"Найден элемент с уроками для пользователя: {item_id}")
                return item

        # Возврат первого элемента, если ничего подходящего не найдено
        logger.info("Подходящие элементы не найдены, возвращаю первый элемент.")
        return items[0]

    except KeyError as e:
        logger.exception(f"Ошибка доступа к данным клиента: отсутствует ключ {e}")
        return None
    except TypeError as e:
        logger.exception(f"Ошибка типа данных при обработке элементов: {e}")
        return None
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка при выборе лучших элементов: {e}")
        return None


async def handle_existing_user(message: Message, session: AsyncSession, is_admin: bool):
    logger.debug("Начало выполнения функции handle_existing_user")
    if is_admin:
        greeting = f'Привет, {"администратор " if is_admin else ""}{message.from_user.username}!'
    else:
        greeting = f"Привет, {message.from_user.username}!"
        user_data = {
            "tg_id": message.from_user.id,
            "username": message.from_user.username,
        }
        logger.debug(f"Данные пользователя из сообщения: {user_data}")

        try:
            logger.debug("Обновление данных пользователя в БД начинается..")
            await orm_update_user(session, user_data=user_data)
            logger.debug(f"Пользователь с tg_id {message.from_user.id} обновлен в БД")

            user = await orm_get_user_by_tg_id(session, tg_id=message.from_user.id)
            logger.debug(f"Получен пользователь из БД: {user}")

            if user:
                user_data["phone_number"] = user.phone_number
                logger.debug(f"Номер телефона пользователя: {user.phone_number}")

                if user.phone_number:
                    logger.debug(
                        f"Поиск пользователя в CRM по номеру телефона: {user.phone_number}"
                    )
                    crm_client = await find_user_by_phone(user.phone_number)
                    logger.debug(f"Клиент из CRM: {crm_client}")

                    logger.debug("Получение лучших элементов для пользователя..")
                    item = await get_best_items(crm_client)
                    logger.debug(f"Лучшие товары для клиента: {item}")

                    logger.debug(
                        "Обработка существующего пользователя с лучшими элементом.."
                    )
                    await process_existing_user(item, session, message, user_data)
                else:
                    logger.error(
                        f"У пользователя с tg_id {message.from_user.id} нет номера телефона."
                    )
            else:
                logger.error(f"Пользователь с tg_id {message.from_user.id} не найден.")

            logger.debug("Данные пользователя успешно обновлены в БД.")

        except Exception as e:
            logger.error(f"Произошла ошибка: {e}")

    logger.debug(f"Отправка приветственного сообщения: {greeting}")
    await message.answer(greeting, reply_markup=main_menu_button_keyboard)
    logger.debug("Приветственное сообщение отправлено")


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
    user = await orm_get_user_by_tg_id(session, tg_id=message.from_user.id)
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

        # Попытка собрать данные пользователя
        try:
            user_data = {
                "tg_id": message.contact.user_id,
                "username": message.from_user.username,
                "first_name": message.contact.first_name,
                "last_name": message.contact.last_name,
                "phone_number": str(message.contact.phone_number),
            }
        except AttributeError as e:
            logger.exception(f"Ошибка при доступе к полям контакта: {e}")
            return await message.answer(
                "Произошла ошибка при обработке вашего контакта. Неверный формат данных."
            )

        # Сохранение данных в базу
        try:
            user = await orm_get_user_by_tg_id(session, tg_id=message.contact.user_id)
            if not user:
                await save_user_data(session, user_data)
            else:
                await update_user_data(session, user_data)
            logger.debug("Основные данные сохранены в БД.")
            await message.answer("Ваш контакт получен. Идет обработка данных...")
        except IntegrityError as e:
            logger.exception(f"Ошибка целостности данных при сохранении в БД: {e}")
            return await message.answer(
                "Произошла ошибка при сохранении ваших данных. Попробуйте позже."
            )
        except OperationalError as e:
            logger.exception(f"Ошибка доступа к базе данных: {e}")
            return await message.answer(
                "Произошла ошибка с базой данных. Попробуйте позже."
            )

        # Проверка, является ли пользователь администратором
        try:
            if check_admin(message.from_user.id):
                await save_user_data(session, user_data)
                return await message.answer(
                    "Спасибо! Ваш контакт сохранен.",
                    reply_markup=main_menu_button_keyboard,
                )
        except Exception as e:
            logger.exception(f"Ошибка при проверке пользователя на администратора: {e}")
            return await message.answer("Произошла ошибка при проверке вашего статуса.")

        # Обработка CRM клиента
        try:
            crm_client = await find_user_by_phone(user_data["phone_number"])
        except ConnectionError as e:
            logger.exception(f"Ошибка при подключении к CRM: {e}")
            return await message.answer("Ошибка связи с CRM. Попробуйте позже.")

        # Получение лучших элементов для клиента
        try:
            item = await get_best_items(crm_client)
        except TimeoutError as e:
            logger.exception(f"Превышено время ожидания при получении элементов: {e}")
            return await message.answer(
                "Произошла ошибка с получением информации. Попробуйте позже."
            )

        # Обработка существующего клиента или создание нового
        if item:
            try:
                await process_existing_user(item, session, message, user_data)
            except Exception as e:
                logger.exception(
                    f"Ошибка при обработке существующего пользователя: {e}"
                )
                return await message.answer(
                    "Произошла ошибка при обработке вашего контакта."
                )
        else:
            try:
                await create_new_user_in_crm(user_data, session, message)
            except Exception as e:
                logger.exception(f"Ошибка при создании нового пользователя в CRM: {e}")
                return await message.answer(
                    "Произошла ошибка при создании нового пользователя. Попробуйте позже."
                )

    except TelegramBadRequest as e:
        logger.exception(f"Ошибка при обработке запроса Telegram: {e}")
        await message.answer(
            "Произошла ошибка при обработке вашего запроса. Попробуйте позже."
        )
    except TelegramNetworkError as e:
        logger.exception(f"Ошибка сети Telegram: {e}")
        await message.answer("Проблема с сетью Telegram. Попробуйте позже.")
    except Exception as e:
        logger.exception(f"Произошла неожиданная ошибка при обработке контакта: {e}")
        await message.answer(
            "Произошла ошибка при обработке вашего контакта. Попробуйте позже."
        )


async def save_user_data(session, user_data):
    logger.debug("Сохраняю данные пользователя в БД.")
    await orm_add_user(session, data=user_data)


async def update_user_data(session, user_data):
    logger.debug("Обновляю данные пользователя в БД.")
    await orm_update_user(session, user_data=user_data)


async def process_existing_user(item, session, message, user_data):
    logger.debug(f"Пользователь с номером {user_data['phone_number']} найден в ЦРМ.")

    user_data.update(
        {
            "user_crm_id": item.get("id"),
            "is_study": item.get("is_study"),
            "user_branch_ids": ",".join(map(str, item.get("branch_ids", []))),
        }
    )

    user_lessons = await get_client_lessons(item.get("id"), item.get("branch_ids", []))
    user_data["user_lessons"] = True if user_lessons.get("total", 0) > 0 else False

    await update_user_data(session, user_data)

    if user_data["user_lessons"]:
        await send_tg_links(message, session, user_data["tg_id"])
    else:
        await message.answer(
            "Спасибо! Ваш контакт сохранен.", reply_markup=main_menu_button_keyboard
        )


async def send_tg_links(message, session, user_id):
    logger.debug("Отправка ссылок на TG.")
    await message.answer("Подготавливаем ссылки... Ожидайте!")
    await message.answer(
        tg_links_message,
        reply_markup=await make_tg_links_inline_keyboard(
            session, user_id, include_back_button=False
        ),
    )
    await message.answer(
        "Спасибо! Ваш контакт сохранен.", reply_markup=main_menu_button_keyboard
    )


async def create_new_user_in_crm(user_data, session, message):
    logger.debug(
        f"Создание нового пользователя с номером {user_data['phone_number']} в ЦРМ."
    )
    response = await create_user_in_alfa_crm(user_data)
    new_user_info = response.get("model", {})
    user_data.update(
        {
            "user_crm_id": new_user_info.get("id", -1),
            "user_branch_ids": ",".join(map(str, new_user_info.get("branch_ids", []))),
            "user_lessons": False,
            "is_study": 0,
            "customer_data": json.dumps(new_user_info),
        }
    )

    await update_user_data(session, user_data)
    await message.answer(greeting_message, reply_markup=main_menu_button_keyboard)

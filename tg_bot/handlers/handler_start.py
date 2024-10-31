import asyncio
import json
from sqlite3 import IntegrityError, OperationalError

from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardRemove

from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from sqlalchemy.exc import IntegrityError, OperationalError
from asyncio import TimeoutError

from tg_bot.database.orm_query import orm_add_user, orm_get_user_by_tg_id, orm_update_user
from tg_bot.filters.filter_admin import check_admin
from tg_bot.crm_logic.alfa_crm_api import (
    create_user_in_alfa_crm,
    find_user_by_phone,
    get_client_lessons,
)
from tg_bot.keyboards.inline_keyboards.inline_keyboard_tg_links import (
    make_tg_links_inline_keyboard,
)
from tg_bot.keyboards.keyboard_send_contact import contact_keyboard

from logger_config import get_logger

logger = get_logger()


start_router: Router = Router()


greeting_message = (
    "Вас приветствует Международная КиберШкола программирования KIBERone!\n"
    "Если вы зашли в этот чат-бот, то мы уверены, что вы заинтересованы в будущем вашего ребенка и знаете, "
    "что изучать программирование сегодня –это даже уже не модно, а НУЖНО! И Вы на правильном пути, ведь мы точно "
    "знаем, чему учить детей, чтобы это было актуально через 20 лет!\n"
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


async def get_best_items(crm_client: dict) -> dict | None:
    try:
        items = crm_client.get("items", [])
        if not items:
            logger.info("Нет доступных элементов в ответе CRM-клиента.")
            return None

        logger.debug(f"Найдено {len(items)} элементов.")

        study_items = []
        for item in items:
            item_id = item.get("id")
            branch_ids = item.get("branch_ids", [])
            is_study = item.get("is_study", 0)

            if item_id is None:
                logger.warning("Пропуск элемента без ID.")
                continue

            logger.debug(f"Обрабатываем элемент ID: {item_id}, branch_ids: {branch_ids}, is_study: {is_study}")

            if is_study == 1:
                try:
                    user_lessons = await get_client_lessons(item_id, branch_ids)
                    if user_lessons and user_lessons.get("total", 0) > 0:
                        study_items.append((item, user_lessons["total"]))
                except Exception as e:
                    logger.exception(f"Ошибка при получении уроков для элемента ID {item_id}: {e}")
                    continue

        if study_items:
            best_item, _ = max(study_items, key=lambda x: x[1])
            logger.info(f"Возвращаем лучший элемент с ID {best_item.get('id')}, "
                        f"у которого есть {max(study_items, key=lambda x: x[1])[1]} занятий.")
            return best_item

        # Если нет подходящих элементов с занятиями, но есть `is_study == 1`
        for item in items:
            if item.get("is_study", 0) == 1:
                logger.info(f"Возвращаем элемент с ID {item.get('id')}, помеченный как 'is_study'.")
                return item

        logger.info("Ни один элемент не подходит по условиям. Возврат первого элемента.")
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
    await message.answer("Добро пожаловать в KIBERone!☺️\n"
                         "Мы рады видеть вас снова!☺️\n"
                         "Сейчас мы немножечко поколдуем для Вас ✨ Ожидайте\n"
                         "")
    if is_admin:
        greeting = f'Привет, {"администратор " if is_admin else ""}{message.from_user.username}!'
    else:
        greeting = f"Привет, {message.from_user.username}!"
        user_data = {
            "tg_id": message.from_user.id,
            "username": message.from_user.username,
        }
        try:
            await orm_update_user(session, user_data=user_data)
            user_in_db = await orm_get_user_by_tg_id(session, tg_id=message.from_user.id)
            logger.debug(user_in_db.phone_number)

            if user_in_db:
                if user_in_db.phone_number:
                    crm_client: dict = await find_user_by_phone(user_in_db.phone_number)

                    if crm_client is None:
                        logger.error(f"CRM клиент с номером {user_in_db.phone_number} не найден.")
                        await message.answer("Не удалось найти данные в CRM.", reply_markup=ReplyKeyboardRemove())
                        return

                    item = await get_best_items(crm_client)

                    if item is None:
                        logger.error(f"Не удалось найти лучшие элементы для клиента {user_in_db.phone_number}.")
                        return

                    await process_existing_user(item, session, message, user_data)

                else:
                    logger.error(f"У пользователя с tg_id {message.from_user.id} нет номера телефона.")
                    await message.answer("У вас не указан номер телефона. Пожалуйста, добавьте его.")
            else:
                logger.error(f"Пользователь с tg_id {message.from_user.id} не найден.")
                await message.answer("Пользователь не найден в базе данных.")

        except Exception as e:
            logger.error(f"Произошла ошибка: {e}")
            await message.answer("Произошла ошибка при обработке вашего запроса.")

    await message.answer(greeting)


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
        \n\n\n
        <b>Нажмите кнопку "Поделиться контактом", чтобы отправить свой контакт.</b>

        <b>С уважением, KIBERone!</b>
        """
    greeting = f"Привет, {message.from_user.username}!\n{formatted_message}"
    logger.debug("Запрашиваю у пользователя контакт..")
    filename = "files/contact_image.png"
    file = types.FSInputFile(filename)
    await message.answer(greeting, reply_markup=contact_keyboard)
    await message.answer_photo(file, caption="Поделитесь своим контактом с KIBERone")


@start_router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession):
    is_admin = check_admin(message.from_user.id)
    user = await orm_get_user_by_tg_id(session, tg_id=message.from_user.id)
    if user:
        await handle_existing_user(message, session, is_admin)
    else:
        await handle_new_user(message)


@start_router.message(F.contact)
async def handle_contact(message: Message, session: AsyncSession):


    await message.answer("Добро пожаловать в KIBERone!☺️\n"
                         "Мы рады видеть вас!☺️\n"
                         "Сейчас мы немножечко поколдуем для Вас ✨ Ожидайте\n"
                         "Это не займет много времени (меньше минуты)\n"
                         "Если бот Вам не отвечает - нажмите снова /start\n"
                         "Наши сервера могут быть очень нагружены..⚡️")
    await asyncio.sleep(0.5)
    await message.answer("Ваш контакт получен. 😊 Идет обработка данных...")
    try:
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
            return await message.answer("Произошла ошибка при обработке вашего контакта. Неверный формат данных.")

        if check_admin(message.from_user.id):
            await save_user_data(session, user_data)
            return await message.answer(
                "Спасибо! Ваш контакт сохранен.", reply_markup=ReplyKeyboardRemove())

        try:
            user = await orm_get_user_by_tg_id(session, tg_id=message.contact.user_id)
            if not user:
                await save_user_data(session, user_data)
            else:
                await update_user_data(session, user_data)
            await message.answer("Ваш контакт сохранен! 😊\nМы подготавливаем для Вас данные.\nЕще пару секундочек..")
        except IntegrityError as e:
            logger.exception(f"Ошибка целостности данных при сохранении в БД: {e}")
            return await message.answer("Произошла ошибка при сохранении ваших данных. Попробуйте позже.")
        except OperationalError as e:
            logger.exception(f"Ошибка доступа к базе данных: {e}")
            return await message.answer("Произошла ошибка с базой данных. Попробуйте позже.")

        try:
            crm_client = await find_user_by_phone(user_data["phone_number"])
        except ConnectionError as e:
            logger.exception(f"Ошибка при подключении к CRM: {e}")
            return await message.answer("Ошибка связи с CRM. Попробуйте позже.")

        try:
            item = await get_best_items(crm_client)
        except TimeoutError as e:
            logger.exception(f"Превышено время ожидания при получении элементов: {e}")
            return await message.answer(
                "Произошла ошибка с получением информации. Попробуйте позже."
            )

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
    logger.debug(f"Обработка существующего пользователя в БД из ЦРМ: {item.get("id")}")

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
        await send_tg_links(message, session, user_data["tg_id"], user_crm_id=item.get("id"), user_branch_ids=user_data["user_branch_ids"])
    else:
        await message.answer(
            "Мы поколдовали, и все готово!", reply_markup=ReplyKeyboardRemove())


async def send_tg_links(message, session, user_id, user_crm_id, user_branch_ids):
    logger.debug("Отправка ссылок на TG.")
    await message.answer("Сейчас мы для Вас подготавливаем ссылки... Ожидайте!😊\n"
                         "Это займет немного времени (меньше 30 секунд)\n"
                         "Если бот не ответил за это время - нажмите команду /start еще раз, пожалуйста!⚡️")

    await message.answer(
        tg_links_message,
        reply_markup=await make_tg_links_inline_keyboard(session, user_id, user_crm_id, user_branch_ids, include_back_button=False),
    )
    await message.answer(
        "Мы поколдовали, и все готово! ✨", reply_markup=ReplyKeyboardRemove())


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
    logger.debug("Данные пользователя в бд обновлены после создания в ЦРМ.")


    await message.answer(greeting_message)

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import get_branch_tg_link, orm_get_user
from crm_logic.alfa_crm_api import (
    find_user_by_phone, get_user_groups_from_crm, get_group_link_from_crm,
)

logger.add(
    "debug.log",
    format="{time} {level} {message}",
    level="ERROR",
    rotation="1 MB",
    compression="zip",
)


async def make_tg_links_inline_keyboard(session: AsyncSession, tg_id: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text="Главный новостной канал KIBERone", url="https://t.me/kiberone_bel"
        )
    ]

    user = await orm_get_user(session, tg_id)
    user_branch_ids: list = list(map(int, user.user_branch_ids.split(',')))
    logger.debug(f"Список городов пользователя: {user_branch_ids}")

    if user_branch_ids:
        for branch_id in user_branch_ids:
            logger.debug("Получение ссылки на чат города из БД..")
            city_link = await get_link_to_branch_chat(session, branch_id=branch_id)
            logger.debug("Формирование кнопки..")
            buttons.append(InlineKeyboardButton(text="Канал города", url=f"{str(city_link)}"))
    else:
        logger.error(f"Не удалось получить ИД города пользователя {user.phone_number}")

    logger.debug("Попытка получить ID пользователя в ЦРМ..")
    user_crm_id: int = user.user_crm_id

    if user_crm_id:
        logger.debug("ID пользователя в ЦРМ получен успешно!")
        logger.debug("Попытка получить список групп пользователя в ЦРМ")
        for branch_id in user_branch_ids:
            group_ids = await get_user_groups_from_crm(branch_id, user_crm_id, session)
            if group_ids:
                for group_id in group_ids:
                    logger.debug("Получение ссылки на группу из БД..")
                    group_link = await get_group_link_from_crm(branch_id, group_id)
                    logger.debug("Формирование кнопки..")
                    if group_link:
                        buttons.append(InlineKeyboardButton(text="Чат группы", url=f"{str(group_link)}"))
                    else:
                        logger.error(f"Не удалось получить ссылку на группу {group_id} для пользователя {user.phone_number}")
            else:
                logger.error(f"Не удалось получить список групп пользователя {user.phone_number}")
    else:
        logger.error(f"Не удалось получить ID пользователя в ЦРМ {user.phone_number}")
    buttons.append(InlineKeyboardButton(text='<< Назад', callback_data='inline_main'))
    logger.debug("Формирование клавиатуры..")
    buttons = [[button] for button in buttons]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Перейдите по ссылкам для вступления в группы..",
    )
    logger.debug("Клавиатура готова! Отправка..")
    return keyboard


async def make_tg_links_inline_keyboard_without_back(session: AsyncSession, tg_id: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text="Главный новостной канал KIBERone", url="https://google.com"
        )
    ]

    user = await orm_get_user(session, tg_id)

    user_branch_ids: list = list(map(int, user.user_branch_ids.split(',')))
    logger.debug(f"Список городов пользователя: {user_branch_ids}")

    if user_branch_ids:
        for branch_id in user_branch_ids:
            logger.debug("Получение ссылки на чат города из БД..")
            city_link = await get_link_to_branch_chat(session, branch_id=branch_id)
            logger.debug("Формирование кнопки..")
            buttons.append(InlineKeyboardButton(text="Канал города", url=f"{str(city_link)}"))
    else:
        logger.error(f"Не удалось получить ИД города пользователя {user.phone_number}")

    logger.debug("Попытка получить ID пользователя в ЦРМ..")
    user_crm_id: int = user.user_crm_id

    if user_crm_id:
        logger.debug("ID пользователя в ЦРМ получен успешно!")
        logger.debug("Попытка получить список групп пользователя в ЦРМ")
        for branch_id in user_branch_ids:
            group_ids = await get_user_groups_from_crm(branch_id, user_crm_id)
            if group_ids:
                for group_id in group_ids:
                    logger.debug("Получение ссылки на группу из БД..")
                    group_link = await get_group_link_from_crm(branch_id, group_id)
                    logger.debug("Формирование кнопки..")
                    if group_link:
                        buttons.append(InlineKeyboardButton(text="Чат группы", url=f"{str(group_link)}"))
                    else:
                        logger.error(f"Не удалось получить ссылку на группу {group_id} для пользователя {user.phone_number}")
            else:
                logger.error(f"Не удалось получить список групп пользователя {user.phone_number}")
    else:
        logger.error(f"Не удалось получить ID пользователя в ЦРМ {user.phone_number}")
    logger.debug("Формирование клавиатуры..")
    buttons = [[button] for button in buttons]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Перейдите по ссылкам для вступления в группы..",
    )
    logger.debug("Клавиатура готова! Отправка..")
    return keyboard


async def get_link_to_branch_chat(session: AsyncSession, branch_id: int):
    query_result = await get_branch_tg_link(session, branch_id=branch_id)
    tg_link = query_result.link
    return tg_link

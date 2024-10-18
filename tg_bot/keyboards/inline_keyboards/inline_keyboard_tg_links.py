from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.crm_logic.alfa_crm_api import get_user_groups_from_crm, get_group_link_from_crm
from tg_bot.database.orm_query import get_branch_tg_link, orm_get_user_by_tg_id

from logger_config import get_logger

logger = get_logger()


async def make_tg_links_inline_keyboard(session: AsyncSession, tg_id: int, user_crm_id, user_branch_ids, include_back_button: bool = True) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text="Главный новостной канал KIBERone", url="https://t.me/kiberone_bel"
        )
    ]

    user_from_bd = await orm_get_user_by_tg_id(session, tg_id)
    user_branch_ids = user_branch_ids

    if not user_from_bd.user_branch_ids:
        logger.warning(f"user_branch_ids is None for user {user_from_bd.phone_number}")
        logger.error(f"Не удалось получить ИД города пользователя {user_from_bd.phone_number}")
    else:
        user_branch_ids: list = list(map(int, user_from_bd.user_branch_ids.split(',')))
        logger.debug(f"Список городов: {user_branch_ids}")
        await add_city_links(session, user_branch_ids, buttons)

    if user_crm_id:
        await add_group_links(session, user_branch_ids, user_crm_id, buttons, user_from_bd.phone_number)
    else:
        logger.error(f"Не удалось получить ID пользователя в ЦРМ чтобы сформировать ссылку "
                     f"на группу пользователя {user_from_bd.phone_number}")

    if include_back_button:
        buttons.append(InlineKeyboardButton(text='<< Назад', callback_data='inline_main'))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[button] for button in buttons],
        resize_keyboard=True,
        input_field_placeholder="Перейдите по ссылкам для вступления в группы..",
    )
    logger.debug("Клавиатура готова! Отправка..")

    return keyboard


async def add_city_links(session: AsyncSession, user_branch_ids: list, buttons: list):
    for branch_id in user_branch_ids:
        logger.debug("Получение ссылки на чат города из БД..")
        city_link = await get_link_to_branch_chat(session, branch_id)
        logger.debug("Формирование кнопки..")
        buttons.append(InlineKeyboardButton(text="Канал города", url=str(city_link)))


async def add_group_links(session: AsyncSession, user_branch_ids: list, user_crm_id: int, buttons: list, phone_number: str):
    logger.debug("Попытка получить список групп пользователя в ЦРМ")
    for branch_id in user_branch_ids:
        group_ids = await get_user_groups_from_crm(branch_id, user_crm_id, session)
        if group_ids:
            for group_id in group_ids:
                logger.debug("Получение ссылки на группу из БД..")
                group_link = await get_group_link_from_crm(branch_id, group_id)
                if group_link:
                    logger.debug("Формирование кнопки..")
                    if group_link.startswith("https://t.me/"):
                        buttons.append(InlineKeyboardButton(text="Чат группы", url=str(group_link)))
                    else:
                        logger.error(f"Не сформировать кнопку на группу {group_id} для пользователя {phone_number}")
                else:
                    logger.error(f"Не удалось получить ссылку на группу {group_id} для пользователя {phone_number}")
        else:
            logger.error(f"Не удалось получить список групп для пользователя {phone_number}")


async def get_link_to_branch_chat(session: AsyncSession, branch_id: int):
    query_result = await get_branch_tg_link(session, branch_id=branch_id)
    return query_result.link
import json

import requests
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import get_branch_tg_link, orm_get_user
from loguru import logger

from tg_bot.handlers.handler_alfacrm import login_to_alfacrm, headers, TEST_CRM_HOSTNAME

logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")


async def make_tg_links_inline_keyboard(session: AsyncSession, tg_id: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text='Главный новостной канал KIBERone',
            url='https://google.com')
    ]

    """
    добавить кнопку на чат города:
    взять юзера из бд по тг, узнать его номер телефона
    получить город, взять из бд ссылку на чат города
    """
    # user = await orm_get_user(session, tg_id)
    # находим юзера по телефону в црм
    data_for_search = {
        "is_study": 0,
        "page": 0,
        "phone": "+375447123218"  # user.phone_number
    }
    data = json.dumps(data_for_search)
    logger.info("Получение токена авторизации..")
    token = login_to_alfacrm()
    client_branch_id = None
    if token:
        headers.update({'X-ALFACRM-TOKEN': token})
        branches = [1, 2, 3]

        for branch in branches:
            try:
                logger.info(f"Поиск клиента в филиале {branch}")
                response = requests.post(f'https://{TEST_CRM_HOSTNAME}/v2api/{branch}/customer/index', headers=headers, data=data)

                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get('total') >= 1:
                        logger.info(f"Пользователь найден. Работаю с его данными..")
                        client_branch_id = response_data["items"][0]["branch_ids"][0]
                        logger.debug(f"client_branch_id: {client_branch_id}")
                        break
                    else:
                        logger.info(f"Клиент в филиале {branch} не найден, поиск в другом филиале")
                else:
                    logger.error(f"Ошибка запроса: {response.status_code} - {response.text}")

            except requests.exceptions.ConnectionError as e:
                logger.error(f"Ошибка соединения: {e}")
            except requests.exceptions.Timeout as e:
                logger.error(f"Тайм-аут запроса: {e}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка при выполнении запроса: {e}")

    # берем ссылку на тг города из БД
    if client_branch_id:
        city_link = await get_link_to_branch_chat(session, branch_id=client_branch_id)
        buttons.append(InlineKeyboardButton(text="Канал города", url=f'{str(city_link)}'))
    else:
        city_link = None

    ----------------------------------------------------------------------------
    """
    добавить кнопку на чат группы:
    взять юзера из бд, узнать его номер телефона
    найти юзера в црм по телефону
    если клиент, то
    получить группу. у группы получить ссылку
    """




    buttons = [[button] for button in buttons]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons, resize_keyboard=True,
                                    input_field_placeholder="Перейдите по ссылкам..")
    return keyboard


async def get_link_to_branch_chat(session: AsyncSession, branch_id: int):
    query_result = await get_branch_tg_link(session, branch_id=branch_id)
    tg_link = query_result.link
    return tg_link

import asyncio
import json
import os
from re import T

import aiohttp
import requests
from loguru import logger

CRM_HOSTNAME = os.getenv("TEST_CRM_HOSTNAME")
CRM_EMAIL = os.getenv("CRM_EMAIL")
CRM_API_KEY = os.getenv("TEST_CRM_API_KEY")

logger.add(
    "../tg_bot/handlers/debug.log",
    format="{time} {level} {message}",
    level="ERROR",
    rotation="1 MB",
    compression="zip",
)

headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "application/json, text/plain, */*",
}

branches = [1, 2, 3]
client_is_study_statuses = [0, 1]


async def login_to_alfa_crm() -> str | None:
    data = {
        "email": CRM_EMAIL,
        "api_key": CRM_API_KEY,
    }

    data = json.dumps(data)
    url = f"https://{CRM_HOSTNAME}/v2api/auth/login"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, data=data) as response:
                response.raise_for_status()
                token_data = await response.json()
                token_from_response = token_data.get("token")

                if token_from_response:
                    logger.debug(f"Токен получен: {token_from_response}")
                    logger.debug("Пауза между запросами в 1 сек..")
                    await asyncio.sleep(1)
                    return token_from_response
                else:
                    logger.debug("Токен не найден в ответе сервера.")
                    return None
        except aiohttp.ClientTimeout as e:
            logger.error(f"Тайм-аут запроса: {e}")
            return None
        except aiohttp.ClientConnectionError as e:
            logger.error(f"Ошибка соединения: {e}")
            return None
        except aiohttp.ClientResponseError as e:
            logger.error(f"Ошибка ответа от клиента: {e}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Произошла ошибка при запросе: {e}")
            return None


async def create_user_in_alfa_crm(user_data: dict):
    client_first_name = user_data.get("first_name", None)
    client_last_name = user_data.get("last_name", None)
    client_name = f'{client_first_name if client_first_name else ""} {client_last_name if client_last_name else ""} | {user_data.get("username", "")}'

    client_phone = user_data.get("phone_number", "")

    data = {
        "name": client_name,
        "phone": client_phone,
        "branch_ids": [1],
        "legal_type": 1,
        "is_study": 0,
        "note": "created by Telegram BOT",
    }
    data = json.dumps(data)

    url = f"https://{CRM_HOSTNAME}/v2api/1/customer/create"

    response_data = await send_request_to_crm(url, data, params=None)
    if response_data.get("success", False):
        logger.info(f"Пользователь в ЦРМ создан!")
    else:
        logger.error(f"Ошибка создания пользователя в ЦРМ: {response_data.get('errors', None)}")


async def find_user_by_phone(phone_number: str) -> dict | None:
    for status in client_is_study_statuses:
        for branch in branches:
            logger.debug(f"Поиск пользователя в филиале: {branch}")
            data = {"is_study": status, "page": 0, "phone": phone_number}
            data = json.dumps(data)
            url = f"https://{CRM_HOSTNAME}/v2api/{branch}/customer/index"
            response_data = await send_request_to_crm(url=url, data=data, params=None)
            if response_data:
                if response_data.get("total") != 0:
                    return response_data
            else:
                return None


async def send_request_to_crm(url: str, data: str, params: dict | None) -> dict | None:
    logger.debug("Получение токена авторизации..")
    token = await login_to_alfa_crm()
    if token:
        logger.debug("Токен получен.")
        logger.debug("Обновление заголовков..")
        headers.update({"X-ALFACRM-TOKEN": token})

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, data=data, params=params, timeout=5) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401:
                        logger.error(f"Неверный токен: {response.status} - {await response.text()}")
                        return None
                    else:
                        logger.error(f"Ошибка запроса: {response.status} - {await response.text()}")
                        return None
            except aiohttp.ClientError as e:
                logger.error(f"Ошибка запроса: {e}")
                return None


async def get_user_groups_from_crm(branch_id: int, user_crm_id: int) -> list | None:
    data = {"page": 0}
    params = {
        "customer_id": user_crm_id,
    }
    data = json.dumps(data)
    url = f"https://{CRM_HOSTNAME}/v2api/{branch_id}/cgi/customer"

    logger.debug(f"Попытка получить группы пользователя (ID): {user_crm_id}")
    response_data = await send_request_to_crm(url=url, data=data, params=params)
    if response_data:
        logger.debug(f"Количество групп пользователя {user_crm_id}: {response_data.get('total', 0)}")
        group_ids = []
        for item in response_data["items"]:
            group_ids.append(item["group_id"])
        logger.debug(f"Группы пользователя (ID): {group_ids}")
        return group_ids
    else:
        logger.error(f"Не удалось получить группы пользователя (ID): {user_crm_id}")
        return None


async def get_group_link_from_crm(branch_id: int, group_id: int) -> str | None:
    data = {"id": group_id, "page": 0}

    data = json.dumps(data)
    url = f"https://{CRM_HOSTNAME}/v2api/{branch_id}/group/index"

    logger.debug(f"Попытка получить ссылку на группу (ID): {group_id}")
    response_data = await send_request_to_crm(url=url, data=data, params=None)
    if response_data:
        logger.debug("Ответ получен. Поиск ссылки..")
        group_tg_link = response_data["items"][0]["note"]
        logger.debug(f"Ссылка на группу: {group_tg_link}")
        return group_tg_link if group_tg_link else None
    else:
        logger.debug("Не удалось получить ссылку на группу.")
        return None


async def check_client_balance_from_crm(phone_number: str) -> int | None:
    data = {"is_study": 1, "page": 0, "phone": phone_number}
    data = json.dumps(data)
    for branch in branches:
        url = f"https://{CRM_HOSTNAME}/v2api/{branch}/customer/index"
        response_data = await send_request_to_crm(url=url, data=data, params=None)
        if response_data:
            if response_data.get("total") != 0:
                logger.debug(f"Попытка получить баланс пользователя..")
                return response_data.get("items", [])[0].get("balance", 0)
        else:
            return None
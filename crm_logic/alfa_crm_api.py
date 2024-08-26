import asyncio
import json
import os
from time import sleep

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_get_user_by_crm_id

load_dotenv()

debug = os.getenv("DEBUG")
if debug == "dev":
    CRM_HOSTNAME = os.getenv("TEST_CRM_HOSTNAME")
    CRM_EMAIL = os.getenv("TEST_CRM_EMAIL")
    CRM_API_KEY = os.getenv("TEST_CRM_API_KEY")
else:
    CRM_HOSTNAME = os.getenv("CRM_HOSTNAME")
    CRM_EMAIL = os.getenv("CRM_EMAIL")
    CRM_API_KEY = os.getenv("CRM_API_KEY")


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
                    logger.debug("Пауза между запросами в 0.5 сек..")
                    await asyncio.sleep(0.5)
                    return token_from_response
                else:
                    logger.debug("Токен не найден в ответе сервера.")
                    return None
        except aiohttp.ClientResponseError as e:
            logger.error(f"Произошла ошибка HTTP-ответа: {e.status} {e.message}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Произошла ошибка клиента aiohttp: {e}")
            return None
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Произошла ошибка соединения клиента aiohttp: {e}")
            return None
        except aiohttp.ClientOSError as e:
            logger.error(f"Произошла ошибка ОС клиента aiohttp: {e}")
            return None
        except Exception as e:
            logger.error(f"Произошла непредвиденная ошибка: {e}")
            return None


async def create_user_in_alfa_crm(user_data: dict):
    token = await login_to_alfa_crm()
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

    response_data = await send_request_to_crm(url, data, params=None, token=token)
    if response_data.get("success", False):
        logger.info(f"Пользователь в ЦРМ создан!")
        return response_data
    else:
        logger.error(f"Ошибка создания пользователя в ЦРМ: {response_data.get('errors', None)}")


async def find_user_by_phone(phone_number: str) -> dict | None:
    token = await login_to_alfa_crm()

    async def fetch_data(branch: str, status: int) -> dict | None:
        data = {"is_study": status, "page": 0, "phone": phone_number}
        data = json.dumps(data)
        url = f"https://{CRM_HOSTNAME}/v2api/{branch}/customer/index"
        return await send_request_to_crm(url=url, data=data, params=None, token=token)

    tasks = [
        fetch_data(str(branch), status)
        for status in client_is_study_statuses
        for branch in branches
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_sum = 0
    count_sum = 0
    all_items = []

    for result in results:
        if isinstance(result, dict):
            total_sum += result.get('total', 0)
            count_sum += result.get('count', 0)
            if 'items' in result:
                all_items.extend(result['items'])
    return {
            "total": total_sum,
            "count": count_sum,
            "items": all_items
        }


async def send_request_to_crm(url: str, data: str, params: dict | None, token: str | None, retries: int = 3, delay: int = 5) -> dict | None:
    token = token
    if token:
        logger.debug("Токен получен.")
        logger.debug("Обновление заголовков..")
        headers.update({"X-ALFACRM-TOKEN": token})
        for attempt in range(retries):
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(url, headers=headers, data=data, params=params, timeout=10) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 401:
                            logger.error(f"Неверный токен: {response.status} - {await response.text()}")
                            return None
                        elif response.status == 429:
                            logger.error(f"Слишком много запросов: {response.status} - {await response.text()}")
                            return None
                        else:
                            logger.error(f"Ошибка запроса: {response.status} - {await response.text()}")
                            return None
                except aiohttp.ClientResponseError as e:
                    logger.error(f"Произошла ошибка HTTP-ответа: {e.status} {e.message}")
                    return None
                except aiohttp.ClientError as e:
                    logger.error(f"Ошибка запроса: {e} (попытка {attempt + 1} из {retries})")
                    if attempt < retries - 1:
                        await asyncio.sleep(delay)
                    else:
                        logger.error("Все попытки отправки запроса исчерпаны.")
                        return None
                except aiohttp.ClientConnectorError as e:
                    logger.error(f"Произошла ошибка соединения клиента aiohttp: {e}")
                    if attempt < retries - 1:
                        await asyncio.sleep(delay)
                    else:
                        logger.error("Все попытки отправки запроса исчерпаны.")
                        return None
                except aiohttp.ClientOSError as e:
                    logger.error(f"Произошла ошибка ОС клиента aiohttp: {e}")
                    if attempt < retries - 1:
                        await asyncio.sleep(delay)
                    else:
                        logger.error("Все попытки отправки запроса исчерпаны.")
                        return None
                except Exception as e:
                    logger.error(f"Произошла непредвиденная ошибка: {e}")
                    return None


async def get_user_groups_from_crm(branch_id: int, user_crm_id: int, session: AsyncSession) -> list | None:
    token = await login_to_alfa_crm()

    user_from_db = await orm_get_user_by_crm_id(session, user_crm_id)
    user_phone = user_from_db.phone_number
    user_from_crm = await find_user_by_phone(phone_number=user_phone)

    user_items = user_from_crm.get("items", [])

    if not user_items:
        logger.error(f"Не удалось получить данные пользователя (ID): {user_crm_id}")
        return None
    else:
        group_ids = []
        for item in user_items:
            user_id = item.get("id")
            logger.debug(f"Получен ID пользователя (ID): {user_id}")

            data = {"page": 0}
            params = {
                "customer_id": user_id,
            }
            data = json.dumps(data)
            url = f"https://{CRM_HOSTNAME}/v2api/{branch_id}/cgi/customer"

            logger.debug(f"Попытка получить группы пользователя (ID): {user_id}")
            response_data = await send_request_to_crm(url=url, data=data, params=params, token=token)
            if response_data:
                logger.debug(f"Количество групп пользователя {user_id}: {response_data.get('total', 0)}")
                for group_item in response_data["items"]:
                    group_ids.append(group_item["group_id"])
                logger.debug(f"Группы пользователя (ID): {group_ids}")
            else:
                logger.error(f"Не удалось получить группы пользователя (ID): {user_id}")
        if not group_ids:
            logger.error(f"Не удалось получить группы пользователя (ID)")
            return None
        else:
            return group_ids


async def get_group_link_from_crm(branch_id: int, group_id: int) -> str | None:
    token = await login_to_alfa_crm()
    data = {"id": group_id, "page": 0}

    data = json.dumps(data)
    url = f"https://{CRM_HOSTNAME}/v2api/{branch_id}/group/index"

    logger.debug(f"Попытка получить ссылку на группу (ID): {group_id}")
    response_data = await send_request_to_crm(url=url, data=data, params=None, token=token)
    if response_data:
        logger.debug("Ответ получен. Поиск ссылки..")
        if response_data.get("total") != 0:
            logger.debug(f"Количество групп: {response_data.get('total', 0)}")
            group_tg_link = response_data.get("items", [])[0].get("note", None)
            logger.debug(f"Ссылка на группу: {group_tg_link}")
            return group_tg_link if group_tg_link else None
    else:
        logger.debug("Не удалось получить ссылку на группу.")
        return None


async def check_client_balance_from_crm(phone_number: str, branch_ids: list, is_study: int) -> str | None:
    token = await login_to_alfa_crm()
    data = {"is_study": is_study, "page": 0, "phone": phone_number}
    data = json.dumps(data)
    for branch in branch_ids:
        url = f"https://{CRM_HOSTNAME}/v2api/{branch}/customer/index"
        response_data = await send_request_to_crm(url=url, data=data, params=None, token=token)
        if response_data:
            logger.debug(response_data)
            if response_data.get("total") != 0:
                logger.debug(f"Попытка получить баланс пользователя..")
                return response_data.get("items", [])[0].get("balance", 0)
        else:
            return None


async def get_client_lessons(user_crm_id: int, branch_ids: list) -> dict | None:
    token = await login_to_alfa_crm()
    data = {
        "customer_id": user_crm_id,
        "status": 1,  # 1 - запланирован урок, 2 - отменен, 3 - проведен
        "lesson_type_id": 2,  # 3 - пробник, 2 - групповой
        "page": 0
    }
    data = json.dumps(data)
    for branch in branch_ids:
        url = f"https://{CRM_HOSTNAME}/v2api/{branch}/lesson/index"
        response_data = await send_request_to_crm(url, data, params=None, token=token)
        if response_data.get("total") != 0:
            return response_data
    return {"total": 0}


async def get_user_trial_lesson(user_crm_id: int, branch_ids: list) -> dict | None:
    token = await login_to_alfa_crm()
    data = {
        "customer_id": user_crm_id,
        "lesson_type_id": 3,  # 3 - пробник, 2 - групповой
        "status": 1,
        "page": 0
    }
    data = json.dumps(data)
    for branch in branch_ids:
        url = f"https://{CRM_HOSTNAME}/v2api/{branch}/lesson/index"
        response_data = await send_request_to_crm(url, data, params=None, token=token)
        if response_data.get("total") != 0:
            return response_data
    return {"total": 0}

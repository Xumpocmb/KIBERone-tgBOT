import asyncio
import json
import os

import requests
from loguru import logger

CRM_HOSTNAME = os.getenv("CRM_HOSTNAME")
TEST_CRM_HOSTNAME = os.getenv("TEST_CRM_HOSTNAME")
CRM_EMAIL = os.getenv("CRM_EMAIL")
CRM_API_KEY = os.getenv("CRM_API_KEY")
TEST_CRM_API_KEY = os.getenv("TEST_CRM_API_KEY")

logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")

headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept': 'application/json, text/plain, */*',
}

branches = [1, 2, 3]
client_is_study_statuses = [0, 1]


async def login_to_alfa_crm():
    data = {
        "email": CRM_EMAIL,
        "api_key": TEST_CRM_API_KEY,
    }

    data = json.dumps(data)
    try:
        response = requests.post(f'https://{TEST_CRM_HOSTNAME}/v2api/auth/login', headers=headers, data=data)
        response.raise_for_status()
        token_data = response.json()
        token_from_response = token_data.get("token")
        if token_from_response:
            logger.debug(f"Токен получен: {token_from_response}")
            logger.debug("Пауза между запросами в 1 сек..")
            await asyncio.sleep(1)
            return token_from_response
        else:
            logger.debug("Токен не найден в ответе сервера.")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Произошла ошибка при запросе: {e}")
        return None


async def create_user_in_alfa_crm(user_data: dict):
    logger.debug("Получение токена авторизации..")
    token = await login_to_alfa_crm()
    if token:
        logger.info(f"Токен получен: {token}")
        await asyncio.sleep(1)
        headers.update({'X-ALFACRM-API-KEY': token})
        client_first_name = user_data.get('first_name', None)
        client_last_name = user_data.get('last_name', None)
        client_name = f'{client_first_name if client_first_name else ""} {client_last_name if client_last_name else ""} | {user_data.get("username", "")}'

        client_phone = user_data.get("phone_number", '')

        data = {
            "name": client_name,
            "phone": client_phone,
            "branch_ids": [1],
            "legal_type": 1,
            "is_study": 0,
            "note": "created by Telegram BOT",
        }
        data = json.dumps(data)

        try:
            response = requests.post(f'https://{TEST_CRM_HOSTNAME}/v2api/1/customer/create', headers=headers, data=data)

            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"Клиент создан: {response_data}")
            else:
                logger.error(f"Ошибка создания клиента: {response.status_code} - {response.text}")

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ошибка соединения: {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Тайм-аут запроса: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Произошла ошибка при запросе: {e}")


async def find_user_by_phone(phone_number: str) -> dict | None:
    for status in client_is_study_statuses:
        for branch in branches:
            logger.debug(f"Поиск пользователя в филиале: {branch}")
            data = {
                "is_study": status,
                "page": 0,
                "phone": phone_number
            }
            data_lead = json.dumps(data)
            url = f'https://{TEST_CRM_HOSTNAME}/v2api/{branch}/customer/index'
            response_data = await send_request_to_crm(url=url, data=data_lead, params=None)
            if response_data:
                if response_data.get('total') != 0:
                    return response_data
            else:
                return None


# async def send_request_for_check_client(data) -> bool:
#     logger.info("Получение токена авторизации..")
#     token = login_to_alfacrm()
#     if token:
#         logger.info(f"Токен получен: {token}")
#         await asyncio.sleep(1)
#         headers.update({'X-ALFACRM-TOKEN': token})
#         for branch in branches:
#             try:
#                 logger.info(f"Поиск клиента в филиале {branch}")
#                 response = requests.post(f'https://{TEST_CRM_HOSTNAME}/v2api/{branch}/customer/index', headers=headers, data=data)
#
#                 if response.status_code == 200:
#                     response_data = response.json()
#                     if response_data.get('total') >= 1:
#                         return True
#                     else:
#                         logger.info(f"Клиент в филиале {branch} не найден, поиск в другом филиале")
#                 else:
#                     logger.error(f"Ошибка запроса: {response.status_code} - {response.text}")
#                     return False
#
#             except requests.exceptions.ConnectionError as e:
#                 logger.error(f"Ошибка соединения: {e}")
#                 return False
#             except requests.exceptions.Timeout as e:
#                 logger.error(f"Тайм-аут запроса: {e}")
#                 return False
#             except requests.exceptions.RequestException as e:
#                 logger.error(f"Ошибка при выполнении запроса: {e}")
#                 return False


async def send_request_to_crm(url, data, params, token):
    logger.info("Получение токена авторизации..")
    token = login_to_alfa_crm()
    if token:
        logger.debug(f"Токен получен")
        logger.debug("Обновление заголовков..")
        headers.update({'X-ALFACRM-TOKEN': token})
        try:
            response = requests.post(url, headers=headers, data=data, params=params if params else None)
            if response.status_code == 200:
                response_data = response.json()
                return response_data
            else:
                logger.error(f"Ошибка запроса: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ошибка соединения: {e}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"Тайм-аут запроса: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            return None

import json

import requests
from loguru import logger

logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")

headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept': 'application/json, text/plain, */*',
}

hostname = "kiberoneminsk.s20.online"
hostname_test = "lera.s20.online"
email = "lera71642@gmail.com"
api_key = "3447236a-89ff-11ee-bc12-3cecefbdd1ae"
api_key_test = "5ce913ee-4f43-11ef-b9b8-3cecefbdd1ae"


def login_to_alfacrm():
    data = {
        "email": email,
        "api_key": api_key_test,
    }

    data = json.dumps(data)
    try:
        response = requests.post(f'https://{hostname_test}/v2api/auth/login', headers=headers, data=data)
        response.raise_for_status()
        token_data = response.json()
        token_from_response = token_data.get("token")
        if token_from_response:
            logger.debug(f"Токен получен: {token_from_response}")
            return token_from_response
        else:
            logger.debug("Токен не найден в ответе сервера.")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Произошла ошибка при запросе: {e}")
        return None


token = login_to_alfacrm()


async def create_lid_alfacrm(user_data: dict):
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
        response = requests.post(f'https://{hostname_test}/v2api/1/customer/create', headers=headers, data=data)

        if response.status_code == 200:
            response_data = response.json()
            logger.debug(f"Клиент создан: {response_data}")
        else:
            logger.error(f"Ошибка создания клиента: {response.status_code} - {response.text}")

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Ошибка соединения: {e}")
    except requests.exceptions.Timeout as e:
        logger.error(f"Тайм-аут запроса: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Произошла ошибка при запросе: {e}")


async def check_client_exists(phone_number: str) -> bool:
    data_for_search = {
        "page": 0,
        "phone": phone_number
    }
    data = json.dumps(data_for_search)
    client_exists: bool = await send_request_for_check_client(data, phone_number)
    if client_exists:
        return True
    else:
        return False


async def send_request_for_check_client(data, client_phone) -> bool:
    headers.update({'X-ALFACRM-TOKEN': token})
    try:
        response = requests.post(f'https://{hostname_test}/v2api/{1}/customer/index', headers=headers, data=data)

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('total') == 0:
                return False
            else:
                return True
        else:
            logger.error(f"Ошибка запроса: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Ошибка соединения: {e}")
        return False
    except requests.exceptions.Timeout as e:
        logger.error(f"Тайм-аут запроса: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при выполнении запроса: {e}")
        return False

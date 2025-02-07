import json
import requests
import time

import aiohttp
from dotenv import load_dotenv
import os
import random

from logger_config import get_logger

logger = get_logger()


load_dotenv()


CRM_HOSTNAME = os.getenv("CRM_HOSTNAME")
CRM_EMAIL = os.getenv("CRM_EMAIL")
CRM_API_KEY = os.getenv("CRM_API_KEY")


headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "application/json, text/plain, */*",
}

branches = [1, 2, 3, 4]
client_is_study_statuses = [0, 1]


def login_to_alfa_crm() -> str | None:
    data = {
        "email": CRM_EMAIL,
        "api_key": CRM_API_KEY,
    }

    url = f"https://{CRM_HOSTNAME}/v2api/auth/login"
    headers = {"Content-Type": "application/json"}

    try:
        time.sleep(random.uniform(0.3, 0.7))
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        token_data = response.json()
        token_from_response = token_data.get("token")

        return token_from_response if token_from_response else None

    except requests.RequestException:
        return None


def find_user_by_phone(phone_number: str) -> dict | None:
    token = login_to_alfa_crm()
    if not token:
        logger.error("Failed to login to Alfa CRM")
        return None

    def fetch_data(branch: str, status: int) -> dict | None:
        data = {"is_study": status, "page": 0, "phone": phone_number}
        data = json.dumps(data)
        url = f"https://{CRM_HOSTNAME}/v2api/{branch}/customer/index"

        response = send_request_to_crm(url=url, data=data, params=None, token=token)
        return response

    results = []
    for status in client_is_study_statuses:
        for branch in branches:
            result = fetch_data(str(branch), status)
            if result is not None:
                results.append(result)

    total_sum = 0
    count_sum = 0
    all_items = []

    for result in results:
        if isinstance(result, dict):
            total_sum += result.get('total', 0)
            count_sum += result.get('count', 0)
            if 'items' in result:
                all_items.extend(result['items'])
        else:
            return None

    return {
        "total": total_sum,
        "count": count_sum,
        "items": all_items
    }


def send_request_to_crm(url: str, data: str, params: dict | None, token: str | None) -> dict | None:
    if token:
        headers.update({"X-ALFACRM-TOKEN": token})
        time.sleep(random.uniform(0.2, 0.6))

        try:
            response = requests.post(url, headers=headers, data=data, params=params, timeout=10)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                return None
            elif response.status_code == 429:
                return None
            else:
                return None

        except requests.RequestException as e:
            return None
    else:
        return None


def get_client_lessons(user_crm_id: int, branch_ids: list, page: int | None = None, status: int = 1) -> dict | None:
    token = login_to_alfa_crm()
    if not token:
        return None

    data = {
        "customer_id": user_crm_id,
        "status": 1,  # 1 - запланирован урок, 2 - отменен, 3 - проведен
        "lesson_type_id": 2,  # 3 - пробник, 2 - групповой
        "page": 0 if page is None else page
    }
    data.update({"status": status})
    data = json.dumps(data)

    for branch in branch_ids:
        url = f"https://{CRM_HOSTNAME}/v2api/{branch}/lesson/index"

        delay = random.uniform(0.3, 0.7)
        time.sleep(delay)

        response_data = send_request_to_crm(url, data, params=None, token=token)
        if response_data and response_data.get("total") != 0:
            return response_data
    return {"total": 0}


def get_client_lesson_name(branch_ids: list, subject_id: int | None = None) -> dict | None:
    token = login_to_alfa_crm()
    if not token:
        return None

    data = {
        "id": subject_id,
        "active": True,
        "page": 0
    }
    data = json.dumps(data)

    for branch in branch_ids:
        url = f"https://{CRM_HOSTNAME}/v2api/{branch}/subject/index"

        delay = random.uniform(0.3, 0.7)
        time.sleep(delay)

        response_data = send_request_to_crm(url, data, params=None, token=token)
        if response_data and response_data.get("total") != 0:
            return response_data
    return {"total": 0}
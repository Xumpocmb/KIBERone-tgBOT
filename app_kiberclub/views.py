import json
import hashlib
import hmac
import os
from hmac import new as hmac_new
import pandas as pd

import gspread
import requests
from bs4 import BeautifulSoup
from django.http import JsonResponse
from urllib.parse import unquote
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv

from app_kiberclub.alfa_crm import find_user_by_phone, get_client_lessons, get_client_lesson_name
from app_kiberclub.models import UserData

load_dotenv()

DEBUG = os.environ.get("BOT_DEBUG")
if DEBUG == "dev":
    BOT_TOKEN = os.environ.get("BOT_TOKEN2")
else:
    BOT_TOKEN = os.environ.get("BOT_TOKEN")

CREDENTIALS_FILE = 'kiberone-tg-bot-a43691efe721.json'


MINSK = {
    '1': "Локация разработки и тестирования ПО",
    '12': "Аэродромная, 125, 4 этаж, кабинет 29",
    '14': "Петра Мстиславца, 1, с торца",
    '15': "ТЦ Арена-Сити, Пр-т Победителей 84, 2 этаж",
    '16': "Неманская, 24, 2 этаж, кабинет 215",
    '19': "Максима Богдановича 132, 2 этаж",
}

MINSK_WORK_SHEET_NAMES = {
    '1': "Локация разработки и тестирования ПО",
    '12': "Аэродромная",
    '14': "Мстиславца",
    '15': "Арена",
    '16': "Неманская",
    '19': "Богдановича",
}

BORISOV = {
    '18': "ТЦ Клад Наполеона, Строителей 26, 3 этаж"
}

BORISOV_WORK_SHEET_NAMES = {
    '18': "Строителей",
}

BARANOVICHI = {
    '17': 'Тельмана, 64, 2 этаж',
    '20': "Р-н Боровки, Geely Центр, пересечение улицы Морфицкого и Журавлевича 1 А, 3 этаж"
}

BARANOVICHI_WORK_SHEET_NAMES = {
    '17': "Радужный",
    '20': "Боровки",
}


worksheet_names = {
    'minsk': MINSK,
    'borisov': BORISOV,
    'baranovichi': BARANOVICHI
}

BARANOVICHI_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1lzGfMTHlpIU4a02OwliKB8pB6vRdl7pTV0TOE2W5ypw'
MINSK_SHEET_URL = 'https://docs.google.com/spreadsheets/d/11KW9qvvAmqUS75SF6o1akKuo2bJPDi7Tomcsf1d1vfc'
BORISOV_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1Q3HI6sl6TvWJkscqpnmm3P-6iANzlENfT4XfHPgqgpQ'


class GoogleSheet:
    def __init__(self, google_credentials_file: str, spreadsheet_url: str, worksheet_name: str) -> None:
        try:
            self.account = gspread.service_account(filename=google_credentials_file)
            self.spreadsheet = self.account.open_by_url(spreadsheet_url)
            self.worksheet_name = worksheet_name
            self.topics = {elem.title: elem.id for elem in self.spreadsheet.worksheets()}
            if worksheet_name not in self.topics:
                raise ValueError(f"Worksheet '{worksheet_name}' not found in spreadsheet")
            self.answers = self.spreadsheet.get_worksheet_by_id(self.topics[worksheet_name])
        except Exception as e:
            print(f"Ошибка подключения к Google Sheets: {e}")
            raise e

    def load_data_from_google_sheet(self) -> pd.DataFrame:
        """Загружает данные из Google Sheets."""
        try:
            if not self.spreadsheet:
                raise ValueError("Spreadsheet is not initialized")
            if not self.topics:
                raise ValueError("No topics found in the spreadsheet")
            worksheet = self.spreadsheet.worksheet(self.worksheet_name)
            if not worksheet:
                raise ValueError(f"Worksheet '{self.worksheet_name}' not found in spreadsheet")
            data = worksheet.get_all_records()
            if not data:
                raise ValueError("No data found in the worksheet")
            df = pd.DataFrame(data)
            return df
        except Exception as e:
            print(f"Ошибка загрузки данных из Google Sheets: {e}")
            raise e


def get_resume(request):
    context = {
        'is_iphone': request.is_iphone,
    }
    return render(request, 'app_kiberclub/client_card.html', context=context)


@csrf_exempt
def get_response_from_page(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            init_data = data.get("initData")

            if not init_data:
                return JsonResponse({"status": "error", "message": "No init data received."}, status=400)

            secret_key = BOT_TOKEN


            init_data_dict = validate(init_data, secret_key)

            if init_data_dict is not None:
                user_info: str = init_data_dict.get("user")
                user_info: dict = json.loads(user_info)
                user_tg_id: int = user_info.get("id")
                try:
                    user_db_info = UserData.objects.filter(tg_id=user_tg_id).first()
                except Exception as e:
                    return JsonResponse({"status": "error", "message": "Ошибка при поиске записи в базе данных"}, status=400)
                user_data_by_phone = find_user_by_phone(user_db_info.phone_number)

                if not user_data_by_phone:
                    return JsonResponse({"status": "error", "message": "Ошибка при поиске в CRM"}, status=400)

                user_crm_items = user_data_by_phone.get("items")
                for item in user_crm_items:
                    user_crm_id: int = item.get("id")
                    user_crm_branch_ids: list = item.get("branch_ids")
                    user_crm_name: str = item.get("name").strip()
                    user_crm_birthday = item.get("dob")

                user_lessons = get_client_lessons(user_crm_id, user_crm_branch_ids)
                if user_lessons['total'] == 0:
                    return JsonResponse({"status": "error", "message": "No lessons found."}, status=400)
                if user_lessons['total'] > user_lessons['count']:
                    page = user_lessons['total'] // user_lessons['count']
                    user_lessons = get_client_lessons(user_crm_id, user_crm_branch_ids, page=page)
                last_user_lesson = user_lessons.get("items", [])[-1]
                subject_id = last_user_lesson.get("subject_id")
                all_lesson_info: dict = get_client_lesson_name(user_crm_branch_ids, subject_id=subject_id)
                if all_lesson_info.get("total") == 0:
                    return JsonResponse({"status": "error", "message": "No lesson names found."}, status=400)
                all_lesson_items: list = all_lesson_info.get("items")

                for item in all_lesson_items:
                    if item.get("id") == subject_id:
                        lesson_name = item.get("name")
                room_id: str = str(last_user_lesson.get("room_id", None))
                if room_id:
                    if room_id in MINSK:
                        room_name = MINSK[room_id]
                        spreadsheet_url = MINSK_SHEET_URL
                        worksheet_name = MINSK_WORK_SHEET_NAMES.get(room_id)
                        location_name = "Минск"
                    elif room_id in BORISOV:
                        room_name = BORISOV[room_id]
                        spreadsheet_url = BORISOV_SHEET_URL
                        worksheet_name = BARANOVICHI_WORK_SHEET_NAMES.get(room_id)
                        location_name = "Борисов"
                    elif room_id in BARANOVICHI:
                        room_name = BARANOVICHI[room_id]
                        spreadsheet_url = BARANOVICHI_SHEET_URL
                        worksheet_name = BARANOVICHI_WORK_SHEET_NAMES.get(room_id)
                        location_name = "Барановичи"
                else:
                    return JsonResponse({"status": "error", "message": "No room info found."}, status=400)

                if not spreadsheet_url or not worksheet_name:
                    return JsonResponse({"status": "error", "message": "No spreadsheet info found."}, status=400)

                google_sheet = GoogleSheet(CREDENTIALS_FILE, spreadsheet_url, worksheet_name)
                df = google_sheet.load_data_from_google_sheet()

                if df is None:
                    return JsonResponse({"status": "error", "message": "No data loaded from Google Sheet"}, status=400)

                for index, row in df.iterrows():
                    if pd.notna(row["ID ребенка"]):
                        if row["ID ребенка"] == user_crm_id:
                            intermediate_resume = row["Резюме промежуточное"]
                            break

                if not intermediate_resume:
                    return JsonResponse({"status": "error", "message": "No intermediate resume found."}, status=400)


                # ----------------------------------------------
                # ПОЛУЧЕНИЕ КИБЕРОНОВ
                # ----------------------------------------------

                with open("kiberclub_credentials.json", "r", encoding="utf-8") as f:
                    data = json.load(f)

                    baranovichi_login: str = data["Барановичи"]["логин"]
                    baranovichi_password: str = data["Барановичи"]["пароль"]

                    minsk_login: str = data["Минск"]["логин"]
                    minsk_password: str = data["Минск"]["пароль"]

                    borisov_login: str = data["Борисов"]["логин"]
                    borisov_password: str = data["Борисов"]["пароль"]

                user_crm_name_splitted: list = user_crm_name.split(" ",)[:2]
                user_crm_name_full: str = " ".join(user_crm_name_splitted)

                if location_name == "Минск":
                    login = minsk_login
                    password = minsk_password
                    kiberons: int | None = get_kiberons_count(user_crm_name_full, login, password)
                elif location_name == "Борисов":
                    login = borisov_login
                    password = borisov_password
                    kiberons: int | None = get_kiberons_count(user_crm_name_full, login, password)
                elif location_name == "Барановичи":
                    login = baranovichi_login
                    password = baranovichi_password
                    kiberons: int | None = get_kiberons_count(user_crm_name_full, login, password)




                return JsonResponse({
                    "status": "success",
                    "message": "Init data received.",
                    "data": {
                        "user_crm_name": user_crm_name or "",
                        "user_crm_birthday": user_crm_birthday or "",
                        "user_crm_location": room_name or "",
                        "lesson_name": lesson_name or "",
                        "intermediate_resume": intermediate_resume or "Появится позже..",
                        "kiberons": kiberons if kiberons is not None else 0,
                    }
                }, status=200)
            else:
                return JsonResponse({"status": "error", "message": "Invalid data received."}, status=400)

        except (json.JSONDecodeError, ValueError) as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"error": "Неподдерживаемый метод"}, status=405)



def validate(init_data: str, token: str, c_str="WebAppData") -> None | dict[str, str]:
    hash_string = ""

    init_data_dict = dict()

    for chunk in init_data.split("&"):
        [key, value] = chunk.split("=", 1)
        if key == "hash":
            hash_string = value
            continue
        init_data_dict[key] = unquote(value)

    if hash_string == "":
        return None

    init_data = "\n".join(
        [
            f"{key}={init_data_dict[key]}"
            for key in sorted(init_data_dict.keys())
        ]
    )

    secret_key = hmac_new(c_str.encode(), token.encode(), hashlib.sha256).digest()
    data_check = hmac_new(secret_key, init_data.encode(), hashlib.sha256)

    if data_check.hexdigest() != hash_string:
        return None

    return init_data_dict


def get_kiberons_count(user_crm_name_full: str, login: str, password: str) -> int | None:
    cookies = {
        'developsess': 'e65294731ff311d892841471f7beec1e',
    }

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ru,en-US;q=0.9,en;q=0.8',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        # 'cookie': 'developsess=e65294731ff311d892841471f7beec1e',
        'origin': 'https://kiber-one.club',
        'priority': 'u=0, i',
        'referer': 'https://kiber-one.club/',
        'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    }

    data = {
        'urltogo': 'https://kiber-one.club/enter/',
        'login': login,
        'password': password,
        'sendloginform': 'Войти',
    }
    response = requests.post('https://kiber-one.club/enter/', cookies=cookies, headers=headers, data=data)

    if response.status_code != 200:
        print("response.status_code != 200")
        return None

    cookies.update(response.cookies)
    headers.update(response.headers)
    users_url = "https://kiber-one.club/mycabinet/users/"

    try:
        response = requests.get(users_url, cookies=cookies, headers=headers)

        if response.status_code != 200:
            print("response.status_code != 200")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    try:
        soup = BeautifulSoup(response.text, 'lxml')
        if soup is None:
            print("No soup found")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    children_elements = soup.find_all("div", class_="user_item")
    if not children_elements:
        print("No children elements found")
        return None

    for child in children_elements:
        name_element = child.find('div', class_='user_admin_col_name').find('a')
        full_name = name_element.text.strip()
        full_name_splitted = full_name.split(' ')[:2]
        name = ' '.join(full_name_splitted)
        if name == user_crm_name_full:
            balance_element = child.find('div', class_='user_admin_col_balance')
            balance = balance_element.text.strip()
            return balance
    return None

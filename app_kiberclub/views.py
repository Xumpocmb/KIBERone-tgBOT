import json
import hashlib
import hmac
from urllib import parse
import os
from hmac import new as hmac_new
import pandas as pd

import gspread
import requests
from bs4 import BeautifulSoup
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from urllib.parse import unquote
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
from gspread import GSpreadException

from app_kiberclub.alfa_crm import find_user_by_phone, get_client_lessons, get_client_lesson_name
from app_kiberclub.models import UserData, Locations


from logger_config import get_logger

logger = get_logger()


load_dotenv()

DEBUG = os.environ.get("BOT_DEBUG")
if DEBUG == "dev":
    BOT_TOKEN = os.environ.get("BOT_TOKEN2")
else:
    BOT_TOKEN = os.environ.get("BOT_TOKEN")

CREDENTIALS_FILE = 'kiberone-tg-bot-a43691efe721.json'

class GoogleSheet:
    def __init__(self, google_credentials_file: str, spreadsheet_url: str, worksheet_name: str) -> None:
        try:
            self.account = gspread.service_account(filename=google_credentials_file)
            self.spreadsheet = self.account.open_by_url(spreadsheet_url)
            self.worksheet_name = worksheet_name
            self.topics = {elem.title: elem.id for elem in self.spreadsheet.worksheets()}
            if worksheet_name not in self.topics:
                raise ValueError(f"Worksheet '{worksheet_name}' not found in spreadsheet")
            self.worksheet = self.spreadsheet.get_worksheet_by_id(self.topics[worksheet_name])
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
            try:
                data = worksheet.get_all_records()
            except Exception as e:
                raise GSpreadException(e)
            if not data:
                raise ValueError("No data found in the worksheet")
            df = pd.DataFrame(data)
            return df
        except Exception as e:
            print(f"Ошибка загрузки данных из Google Sheets: {e}")
            raise e

    def add_data_to_google_sheet(self, user_crm_id, feedback):
        """Добавляет фидбек от родителя в Google Sheets."""
        try:
            df = self.load_data_from_google_sheet()

            row_index = df[df['ID ребенка'] == user_crm_id].index
            if row_index.empty:
                raise ValueError(f"Child with ID {user_crm_id} not found in the worksheet")

            row_number = row_index[0] + 2  # +2, потому что индексы DataFrame начинаются с 0, а индексы Google Sheets с 1
            self.worksheet.update_cell(row_number, df.columns.get_loc('Отзыв родителя') + 1, feedback)

        except Exception as e:
            print(f"Ошибка добавления данных в Google Sheets: {e}")
            raise e

    def save_data_to_google_sheet(self, df: pd.DataFrame, worksheet_name) -> None:
        """Сохраняет DataFrame в указанный лист Google Sheets."""
        try:
            if not self.spreadsheet:
                raise ValueError("Spreadsheet is not initialized")
            if not self.topics:
                raise ValueError("No topics found in the spreadsheet")
            worksheet = self.spreadsheet.worksheet(worksheet_name)
            if not worksheet:
                raise ValueError(f"Worksheet '{worksheet_name}' not found in spreadsheet")
            worksheet.clear()
            worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        except Exception as e:
            raise e


def index(request):
    context = {
        'is_iphone': request.is_iphone,
        "title": "KIBERone",
    }
    return render(request, 'app_kiberclub/greetings.html', context=context)


def choose_child(request):
    user_crm_items = request.session.get('user_crm_items', [])
    if not user_crm_items:
        return redirect('app_kiberclub:error_page')
    profiles = {}
    for item in user_crm_items:
        profiles.update({item.get("id"): item.get("name")})
    context = {
        'is_iphone': request.is_iphone,
        "profiles": profiles,
    }
    return render(request, 'app_kiberclub/choose_child.html', context=context)


def error_page(request):
    context = {
        'is_iphone': request.is_iphone,
    }
    return render(request, 'app_kiberclub/error_page.html', context=context)


def get_user_crm_items(request):
    logger.debug("get_user_crm_items called")

    user_tg_id = request.session.get('user_tg_id')
    logger.debug(f"User Telegram ID from session: {user_tg_id}")

    if not user_tg_id:
        logger.error("No user_tg_id found in session.")
        return redirect('app_kiberclub:error_page')

    try:
        user_db_info = UserData.objects.filter(tg_id=user_tg_id).first()
        logger.debug(f"User database info: {user_db_info}")
    except Exception as e:
        logger.error(f"Error fetching user data from database: {e}")
        return redirect('app_kiberclub:error_page')
        # return JsonResponse({"status": "error", "message": "Ошибка при поиске записи в базе данных"}, status=404)

    if not user_db_info:
        logger.error("No user data found in the database.")
        return redirect('app_kiberclub:error_page')

    try:
        user_data_by_phone = find_user_by_phone(user_db_info.phone_number)
        logger.debug(f"User data by phone: {user_data_by_phone}")
    except Exception as e:
        logger.error(f"Error finding user by phone: {e}")
        return redirect('app_kiberclub:error_page')

    if not user_data_by_phone:
        logger.error("No user data found by phone.")
        return redirect('app_kiberclub:error_page')

    user_crm_items = user_data_by_phone.get('items')
    logger.debug(f"User CRM items: {user_crm_items}")

    return user_crm_items


# @csrf_exempt
def save_init_data(request):
    logger.debug("save_init_data called")

    if request.method == 'POST':
        logger.debug("Request method is POST")
        try:
            data = json.loads(request.body)
            logger.debug(f"Request body loaded: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {e}")
            return JsonResponse({"status": "error", "message": "Invalid JSON data."}, status=400)

        init_data = data.get('initData')
        if not init_data:
            logger.error("No init data received.")
            return JsonResponse({"status": "error", "message": "No init data received."}, status=400)

        secret_key = BOT_TOKEN
        logger.debug(f"Secret key: {secret_key}")

        init_data_dict = validate(init_data, secret_key)
        if init_data_dict is None:
            logger.error("Invalid data received.")
            return JsonResponse({"status": "error", "message": "Invalid data received."}, status=400)

        logger.debug(f"init_data_dict: {init_data_dict}")

        try:
            user_dict = json.loads(init_data_dict.get('user'))
            logger.debug(f"User dictionary: {user_dict}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode user JSON: {e}")
            return JsonResponse({"status": "error", "message": "Invalid user data."}, status=400)

        user_tg_id = user_dict.get('id')
        logger.debug(f"User Telegram ID: {user_tg_id}")
        request.session['user_tg_id'] = user_tg_id

        user_crm_items = get_user_crm_items(request)
        logger.debug(f"User CRM items: {user_crm_items}")

        if not user_crm_items:
            logger.error("No user CRM items received.")
            return redirect('app_kiberclub:error_page')

        try:
            request.session['user_crm_items'] = user_crm_items
            logger.debug("User CRM items saved to session.")
        except Exception as e:
            logger.error(f"Failed to save user CRM items to session: {e}")
            return redirect('app_kiberclub:error_page')

        return JsonResponse({'status': 'success'})

    logger.error("Invalid request method.")
    return JsonResponse({'status': 'invalid request'}, status=400)


def open_profile(request):
    context = {
        'is_iphone': request.is_iphone,
    }
    if request.method == 'POST':
        profile_id = request.POST.get('profile_id')


        user_crm_items = request.session.get('user_crm_items', [])
        if not user_crm_items:
            return redirect('app_kiberclub:error_page')

        for item in user_crm_items:
            if int(item.get('id')) == int(profile_id):
                user_crm_id = item.get("id")
                request.session['user_crm_id'] = user_crm_id
                user_crm_branch_ids = item.get("branch_ids")
                request.session['user_crm_branch_ids'] = user_crm_branch_ids
                user_crm_name = item.get("name").strip()
                user_crm_birthday = item.get("dob")

                context.update({
                    "user_crm_id": user_crm_id,
                    "user_crm_name": user_crm_name,
                    "user_tg_id": request.session.get('user_tg_id'),
                })

                lesson_name, room_id = get_user_lessons(user_crm_id, user_crm_branch_ids)
                if lesson_name and room_id:
                    context.update({
                        "lesson_name": lesson_name if lesson_name else "У вас нет занятий",
                        "room_id": room_id,
                    })
                else:
                    return redirect('app_kiberclub:error_page')

                if room_id:
                    room_name, spreadsheet_url, worksheet_name, branch_id = get_room_id(room_id)
                    request.session['room_id'] = room_id
                    request.session['room_name'] = room_name
                    request.session['spreadsheet_url'] = spreadsheet_url
                    request.session['worksheet_name'] = worksheet_name
                    request.session['branch_id'] = branch_id
                    if not room_name:
                        context.update({"user_location": "Неизвестно"})
                    else:
                        context.update({"user_location": room_name})
                    if not spreadsheet_url or not worksheet_name:
                        context.update({"user_resume": "Появится позже"})
                    else:
                        user_resume = get_intermediate_resume_from_spreadsheet(spreadsheet_url, worksheet_name, user_crm_id)
                        if user_resume:
                            context.update({"user_resume": user_resume})
                        else:
                            context.update({"user_resume": "Появится позже"})
                else:
                    context.update({"user_resume": "Появится позже"})

                if user_crm_name and branch_id:
                    kiberons_count = get_check_kiberclub(request.session.get('user_tg_id'), user_crm_id, user_crm_name, branch_id)
                    context.update({"user_kiberons": kiberons_count if kiberons_count else 0})
                else:
                    context.update({"user_kiberons": 0})

                break

    return render(request, 'app_kiberclub/client_card.html', context=context)


def submit_review(request):
    if request.method == 'POST':
        user_crm_id = request.session.get('user_crm_id')
        room_id = request.session.get('room_id')
        room_name = request.session.get('room_name')
        spreadsheet_url = request.session.get('spreadsheet_url')
        worksheet_name = request.session.get('worksheet_name')
        branch_id = request.session.get('branch_id')
        feedback = request.POST.get('feedbackInput')

        if user_crm_id and room_id and room_name and spreadsheet_url and worksheet_name and branch_id:
            if save_review(user_crm_id, spreadsheet_url, worksheet_name, feedback):
                return JsonResponse({'status': 'success', "message": "Ваш отзыв сохранен!"}, status=200)
    return JsonResponse({'status': 'error', "message": "Произошла ошибка при сохранении отзыва"}, status=400)


def save_review(user_crm_id, spreadsheet_url, worksheet_name, feedback):
    google_sheet = GoogleSheet(CREDENTIALS_FILE, spreadsheet_url, worksheet_name)
    try:
        google_sheet.add_data_to_google_sheet(user_crm_id, feedback)
        return True
    except Exception as e:
        return False


def get_intermediate_resume_from_spreadsheet(spreadsheet_url, worksheet_name, user_crm_id):

    google_sheet = GoogleSheet(CREDENTIALS_FILE, spreadsheet_url, worksheet_name)
    df = google_sheet.load_data_from_google_sheet()

    if df is None:
        return JsonResponse({"status": "error", "message": "No data loaded from Google Sheet"}, status=400)

    for index, row in df.iterrows():
        if pd.notna(row["ID ребенка"]):
            if row["ID ребенка"] == user_crm_id:
                intermediate_resume = row["Резюме промежетучное 2025"]
                return intermediate_resume


def get_check_kiberclub(tg_id, user_crm_id, user_crm_name, branch_id):
    with open("kiberclub_credentials.json", "r", encoding="utf-8") as f:
        data = json.load(f)

        baranovichi_login: str = data["Барановичи"]["логин"]
        baranovichi_password: str = data["Барановичи"]["пароль"]

        minsk_login: str = data["Минск"]["логин"]
        minsk_password: str = data["Минск"]["пароль"]

        borisov_login: str = data["Борисов"]["логин"]
        borisov_password: str = data["Борисов"]["пароль"]

        novopolock_login: str = data["Новополоцк"]["логин"]
        novopolock_password: str = data["Новополоцк"]["пароль"]

    user_crm_name_splitted: list = user_crm_name.split(" ", )[:2]
    user_crm_name_full: str = " ".join(user_crm_name_splitted)

    if branch_id == 1:
        login = minsk_login
        password = minsk_password
        kiberons: int | None = get_kiberons_count(tg_id, user_crm_id, user_crm_name_full, login, password)
        return kiberons
    elif branch_id == 3:
        login = borisov_login
        password = borisov_password
        kiberons: int | None = get_kiberons_count(tg_id, user_crm_id, user_crm_name_full, login, password)
        return kiberons
    elif branch_id == 2:
        login = baranovichi_login
        password = baranovichi_password
        kiberons: int | None = get_kiberons_count(tg_id, user_crm_id, user_crm_name_full, login, password)
        return kiberons
    elif branch_id == 4:
        login = novopolock_login
        password = novopolock_password
        kiberons: int | None = get_kiberons_count(tg_id, user_crm_id, user_crm_name, login, password)
        return kiberons


def get_room_id(room_id):
    room_id = int(room_id)
    try:
        location_info = Locations.objects.get(location_id=room_id)
        room_name = location_info.location_name
        spreadsheet_url = location_info.sheet_url
        worksheet_name = location_info.sheet_names
        return room_name, spreadsheet_url, worksheet_name, location_info.location_branch_id
    except Exception:
        return None, None, None, None


def get_user_lessons(user_crm_id, user_crm_branch_ids):
    lesson_name: str | None = None
    room_id = None

    user_lessons = get_client_lessons(user_crm_id, user_crm_branch_ids)
    if user_lessons['total'] > 0:
        if user_lessons['total'] > user_lessons['count']:
            page = user_lessons['total'] // user_lessons['count']
            user_lessons = get_client_lessons(user_crm_id, user_crm_branch_ids, page=page)
        last_user_lesson = user_lessons.get("items", [])[-1]
        room_id: str | None = str(last_user_lesson.get("room_id", None))

        subject_id = last_user_lesson.get("subject_id")
        all_lesson_info: dict = get_client_lesson_name(user_crm_branch_ids, subject_id=subject_id)
        if all_lesson_info.get("total") > 0:
            all_lesson_items: list = all_lesson_info.get("items")
            for item in all_lesson_items:
                if item.get("id") == subject_id:
                    lesson_name = item.get("name")

    return lesson_name, room_id


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


def get_kiberons_count(tg_id, user_crm_id, user_crm_name_full: str, login: str, password: str) -> int | None:
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
        return None

    cookies.update(response.cookies)
    headers.update(response.headers)
    users_url = "https://kiber-one.club/mycabinet/users/"

    try:
        response = requests.get(users_url, cookies=cookies, headers=headers)

        if response.status_code != 200:
            return None
    except Exception as e:
        return None

    try:
        soup = BeautifulSoup(response.text, 'lxml')
        if soup is None:
            return None
    except Exception as e:
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
        if name == ' '.join(user_crm_name_full.split(' ')[:2]):
            balance_element = child.find('div', class_='user_admin_col_balance')
            balance = balance_element.text.strip()

            user = UserData.objects.filter(tg_id=tg_id).first()
            if user:
                user.kiberons_count = int(balance)
                user.save()
            else:
                return 0
            return balance
    return None


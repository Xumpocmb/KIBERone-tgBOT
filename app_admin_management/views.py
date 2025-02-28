import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
import gspread
import pandas as pd
import logging
from app_admin_management.forms import UploadExcelFileForm
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile




logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(lineno)d - %(message)s'
)

CREDENTIALS_FILE = 'kiberone-tg-bot-a43691efe721.json'


def index_admin(request):
    return render(request, 'app_admin_management/index_admin.html')


def user_data_from_excel(request):
    if request.method == 'POST':
        form = UploadExcelFileForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['file']
            file_path = default_storage.save('tmp/' + excel_file.name, ContentFile(excel_file.read()))
            tmp_file = os.path.join(default_storage.location, file_path)
            location_name = form.cleaned_data['location_name']
            sheet_url = form.cleaned_data['sheet_url']
            sheet_names = form.cleaned_data['sheet_names']

            # обработка
            excel_df = pd.read_excel(excel_file)
            google_sheet = GoogleSheet(CREDENTIALS_FILE, sheet_url, sheet_names)
            google_sheet.add_new_rows(excel_df)

            default_storage.delete(file_path)

            messages.success(request, 'File uploaded and processed successfully!', extra_tags='success')
            return redirect('app_admin_management:user_data_from_excel')

        else:
            messages.error(request, 'File upload failed!', extra_tags='danger')
            return redirect('app_admin_management:user_data_from_excel')
    else:
        form = UploadExcelFileForm()
    return render(request, 'app_admin_management/user_data_from_excel.html', {'form': form})



# Настройка логирования


class GoogleSheet:
    def __init__(self, google_credentials_file: str, spreadsheet_url: str, worksheet_name: str) -> None:
        try:
            self.account = gspread.service_account(filename=google_credentials_file)
            self.spreadsheet = self.account.open_by_url(spreadsheet_url)
            self.worksheet = self.spreadsheet.worksheet(worksheet_name)
        except Exception as e:
            logging.error(f"Ошибка подключения к Google Sheets: {e}")
            raise e

    def get_existing_ids(self) -> set:
        """Загружает существующие ID из Google Sheets для быстрого сравнения."""
        try:
            column_values = self.worksheet.col_values(1)  # Получаем только первый столбец (ID)
            return set(column_values[1:])  # Пропускаем заголовок
        except Exception as e:
            logging.error(f"Ошибка при загрузке ID из Google Sheets: {e}")
            return set()

    def add_new_rows(self, excel_df: pd.DataFrame):
        """Добавляет новые строки из Excel, если их нет в Google Sheets."""
        try:
            existing_ids = self.get_existing_ids()
            logging.info(f"Найдено {len(existing_ids)} существующих записей в Google Sheets.")

            new_rows = [
                [
                    str(row["ID"]),  # ID ребенка
                    row["ФИО"],      # ФИО ребенка
                    row["Группы"],   # Группа
                    "", "", "", ""   # Пустые колонки для резюме и отзыва
                ]
                for _, row in excel_df.iterrows() if str(row["ID"]) not in existing_ids
            ]

            if new_rows:
                self.worksheet.append_rows(new_rows, value_input_option="RAW")
                logging.info(f"Добавлено {len(new_rows)} новых строк в Google Sheets.")
            else:
                logging.info("Нет новых данных для добавления.")
        except Exception as e:
            logging.error(f"Ошибка при добавлении новых данных: {e}")
            raise e




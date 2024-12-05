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
            google_sheet.update_google_sheet_with_excel(excel_df)

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
            self.worksheet_name = worksheet_name
            self.topics = {elem.title: elem.id for elem in self.spreadsheet.worksheets()}
            if worksheet_name not in self.topics:
                raise ValueError(f"Worksheet '{worksheet_name}' not found in spreadsheet")
            self.worksheet = self.spreadsheet.get_worksheet_by_id(self.topics[worksheet_name])
        except Exception as e:
            logging.error(f"Ошибка подключения к Google Sheets: {e}")
            raise e

    def load_data_from_google_sheet(self) -> pd.DataFrame:
        """Загружает данные из Google Sheets."""
        try:
            data = self.worksheet.get_all_records()
            if not data:
                raise ValueError("No data found in the worksheet")
            df = pd.DataFrame(data)
            return df
        except Exception as e:
            logging.error(f"Ошибка загрузки данных из Google Sheets: {e}")
            raise e

    def update_google_sheet_with_excel(self, excel_df: pd.DataFrame):
        """Обновляет Google Sheets данными из Excel-таблицы."""
        try:
            # Загрузить данные из Google Sheets
            logging.info("Загрузка данных из Google Sheets...")
            google_df = self.load_data_from_google_sheet()
            logging.info("Данные из Google Sheets успешно загружены.")

            # Сравнить данные и добавить новые строки
            logging.info("Начало сравнения данных из Excel-файла с данными из Google Sheets...")
            new_rows = []
            for index, row in excel_df.iterrows():
                user_crm_id = row['ID']
                logging.debug(f"Обработка строки с ID ребенка: {user_crm_id}")
                if user_crm_id not in google_df['ID ребенка'].values:
                    new_row = [
                        user_crm_id,  # ID ребенка
                        row['ФИО'],  # ФИО ребенка
                        row['Группы'],  # Группа
                        '',  # Резюме промежуточное
                        '',  # Резюме НГ
                        '',  # Резюме май 2025
                        ''  # Отзыв родителя
                    ]
                    new_rows.append(new_row)
                    logging.info(f"Добавление новой строки в Google Sheets: {new_row}")
                else:
                    logging.debug(f"ID ребенка {user_crm_id} уже существует в Google Sheets.")

            if new_rows:
                logging.info("Выполнение пакетного обновления Google Sheets...")
                # Получаем текущий размер таблицы
                current_row_count = len(google_df) + 1
                # Подготавливаем данные для пакетного обновления
                batch_update_data = {
                    'range': f'A{current_row_count}:G{current_row_count + len(new_rows) - 1}',
                    'values': new_rows
                }
                self.worksheet.batch_update([{
                    'range': batch_update_data['range'],
                    'values': batch_update_data['values']
                }])
                logging.info("Пакетное обновление Google Sheets успешно выполнено.")
            else:
                logging.info("Нет новых строк для добавления.")

            logging.info("Сравнение данных завершено.")

        except Exception as e:
            logging.error(f"Ошибка обновления Google Sheets данными из Excel: {e}")
            raise e




import json
import os


def read_click_data(file_path='click_data.json'):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}


def write_click_data(data, file_path='click_data.json'):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def increment_click_count(callback_data, file_path='click_data.json'):
    data = read_click_data(file_path)
    if callback_data in data:
        data[callback_data] += 1
    else:
        data[callback_data] = 1
    write_click_data(data, file_path)

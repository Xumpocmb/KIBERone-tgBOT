import csv
import json
import os
from sqlalchemy import select
from aiogram import Router, F, types
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.database.engine import session_maker
from tg_bot.database.models import Partner
from tg_bot.middlewares.middleware_database import DataBaseSession

admin_handler_parthner_statistic_router: Router = Router()
admin_handler_parthner_statistic_router.callback_query.middleware(
    DataBaseSession(session_pool=session_maker)
)

@admin_handler_parthner_statistic_router.callback_query(F.data == "parthner_statistic")
async def tasks_list_handler(callback: CallbackQuery, session: AsyncSession):
    json_file_name = "click_data.json"
    csv_file_name = "parthner_statistic.csv"

    if not os.path.exists(json_file_name):
        await callback.message.answer("Данные для статистики не найдены.")
        await callback.answer()
        return

    with open(json_file_name, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)

    with open(csv_file_name, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file, delimiter=';')
        writer.writerow(['Ключ', 'Значение'])

        for key, value in data.items():
            partner_id = int(key.split('-')[1])
            query = select(Partner).where(Partner.id == partner_id)
            result = await session.execute(query)
            partner = result.scalar()
            partner_name = partner.partner
            writer.writerow([partner_name, value])


    file = types.FSInputFile(csv_file_name)
    await callback.message.answer_document(file)

    os.remove(csv_file_name)
    await callback.answer()

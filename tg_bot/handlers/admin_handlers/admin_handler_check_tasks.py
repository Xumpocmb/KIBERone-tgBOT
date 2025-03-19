import csv
import io
import os
from datetime import datetime

from aiogram import Router, F, types
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.database.engine import session_maker
from tg_bot.database.orm_query import get_tasks
from tg_bot.middlewares.middleware_database import DataBaseSession

admin_tasks_list_router: Router = Router()
admin_tasks_list_router.callback_query.middleware(
    DataBaseSession(session_pool=session_maker)
)

@admin_tasks_list_router.callback_query(F.data == "tasks_list")
async def tasks_list_handler(callback: CallbackQuery, session: AsyncSession):
    tasks_in_db = await get_tasks(session)

    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    csv_writer.writerow(["ID", "Next Run Time"])
    for task in tasks_in_db:
        csv_writer.writerow([task.id, task.next_run_time])
    csv_buffer.seek(0)

    temp_filename = f"tasks_{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.csv"
    with open(temp_filename, 'wb') as f:
        f.write(csv_buffer.getvalue().encode('utf-8'))

    file = types.FSInputFile(temp_filename)
    await callback.message.answer_document(file)

    os.remove(temp_filename)
    await callback.answer()

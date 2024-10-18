import csv
from datetime import datetime
import io
import os
from aiogram import Router, F, types
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.database.engine import session_maker
from tg_bot.database.orm_query import get_all_users
from tg_bot.middlewares.middleware_database import DataBaseSession


admin_user_list_router: Router = Router()
admin_user_list_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))


@admin_user_list_router.callback_query(F.data == "admin_user_list")
async def user_list_handler(callback: CallbackQuery, session: AsyncSession):
    users_in_db = await get_all_users(session)

    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    csv_writer.writerow(["ID", "Name", "Phone", "Created"])
    for user in users_in_db:
        csv_writer.writerow([user.id, user.last_name if user.last_name else user.username,
                             user.phone_number, user.created_at])
    csv_buffer.seek(0)

    temp_filename = f"users_{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.csv"
    with open(temp_filename, 'wb') as f:
        f.write(csv_buffer.getvalue().encode('utf-8'))

    file = types.FSInputFile(temp_filename)
    await callback.message.answer_document(file)

    os.remove(temp_filename)
    await callback.answer()

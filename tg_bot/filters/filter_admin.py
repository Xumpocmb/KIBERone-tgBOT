import os
from aiogram import Router
from aiogram.filters import Filter
from aiogram.types import Message
from dotenv import load_dotenv


load_dotenv()
router = Router()


admins_list = [int(admin_id) for admin_id in os.getenv("ADMINS").split(",")]


def check_admin(user_id: int) -> bool:
    return user_id in admins_list

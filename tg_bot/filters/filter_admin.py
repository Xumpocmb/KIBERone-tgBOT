import os
from aiogram import Router
from aiogram.filters import Filter
from aiogram.types import Message
from dotenv import load_dotenv


load_dotenv()
router = Router()


admins_list = [int(admin_id) for admin_id in os.getenv("ADMINS").split(",")]


class AdminFilter(Filter):
    def __init__(self, admin: bool) -> None:
        """
        Initializes the AdminFilter class with the provided admin boolean parameter.

        Parameters:
            admin (bool): A boolean indicating if the user is an admin.

        Returns:
            None
        """
        self.admin = admin

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in admins_list

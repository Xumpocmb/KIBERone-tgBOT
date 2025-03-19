import datetime
from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class AntiFloodMiddleware(BaseMiddleware):
    time_updates: dict[int, datetime.datetime] = {}
    timedelta_limiter: datetime.timedelta = datetime.timedelta(seconds=3)

    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject,
                       data: Dict[str, Any]) -> Any:
        """
        This method is called when the middleware is invoked. It checks if the event is a Message or CallbackQuery,
        retrieves the user_id from the event, and then verifies if the user has made an event within the timedelta limit.
        If the conditions are met, it updates the time_updates dictionary and calls the handler for the event, returning its result.

        Parameters:
            handler (Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]]): The handler function to call.
            event (TelegramObject): The event object being handled.
            data (Dict[str, Any]): Additional data associated with the event.

        Returns:
            Any: The result of calling the handler function for the event.
        """
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
            if user_id in self.time_updates.keys():
                if (datetime.datetime.now() - self.time_updates[user_id]) > self.timedelta_limiter:
                    self.time_updates[user_id] = datetime.datetime.now()
                    return await handler(event, data)
            else:
                self.time_updates[user_id] = datetime.datetime.now()
                return await handler(event, data)

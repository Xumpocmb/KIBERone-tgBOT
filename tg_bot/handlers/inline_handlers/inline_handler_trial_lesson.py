from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from crm_logic.alfa_crm_api import find_user_by_phone, get_user_trial_lesson
from database.engine import session_maker
from database.orm_query import orm_get_user_by_tg_id
from tg_bot.middlewares.middleware_database import DataBaseSession


trial_lesson_router: Router = Router()
trial_lesson_router.callback_query.middleware(
    DataBaseSession(session_pool=session_maker)
)

week = {
    "0": "Понедельник",
    "1": "Вторник",
    "2": "Среда",
    "3": "Четверг",
    "4": "Пятница",
    "5": "Суббота",
    "6": "Воскресенье",
}

MINSK = {
    "1": "Локация разработки и тестирования ПО",
    "12": "Аэродромная, 125, 4 этаж, кабинет 29",
    "14": "Петра Мстиславца, 1, с торца",
    "15": "ТЦ Арена-Сити, Пр-т Победителей 84, 2 этаж",
    "16": "Неманская, 24, 2 этаж, кабинет 215",
    "19": "Максима Богдановича 32, 2 этаж",
}

BORISOV = {"18": "ТЦ Клад Наполеона, Строителей 26, 3 этаж"}

BARANOVICHI = {
    "17": "Тельмана, 64, 2 этаж",
    "20": "Р-н Боровки, Geely Центр, пересечение улицы Морфицкого и Журавлевича 1 А, 3 этаж",
}


@trial_lesson_router.callback_query(F.data == "user_trial_date")
async def user_trial_handler(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    logger.debug(
        f"Начало обработки запроса на пробное занятие от пользователя с ID: {user_id}"
    )

    try:
        await callback.message.edit_text(
            text="Ожидайте пожалуйста, проверяю Ваше расписание.."
        )
        logger.debug(f"Сообщение пользователю с ID {user_id} изменено на 'Ожидайте...'")

        # Получаем информацию о пользователе
        user_in_db = await orm_get_user_by_tg_id(session, user_id)
        user_in_crm = await find_user_by_phone(user_in_db.phone_number)

        if user_in_crm.get("total", 0):
            items = user_in_crm.get("items", [])
            for item in items:
                if item.get("is_study", 0) == 0:
                    user_crm_name = item.get("name", None)
                    user_crm_id = item.get("id", None)
                    user_branch_ids = item.get("branch_ids", [])
                    user_lessons = await get_user_trial_lesson(
                        user_crm_id, user_branch_ids
                    )
                    if user_lessons.get("total", 0) > 0:
                        trial_lesson = user_lessons.get("items", [])[0]
                        logger.debug(
                            f"Пробное занятие для пользователя с ID {user_crm_id}: {trial_lesson}"
                        )

                        lesson_date = trial_lesson.get("date", None)
                        if lesson_date:
                            logger.debug(
                                f"Дата занятия для пользователя с ID {user_crm_id}: {lesson_date}"
                            )
                            lesson_date = lesson_date.split("-")
                            lesson_date_splitted = datetime(
                                int(lesson_date[0]),
                                int(lesson_date[1]),
                                int(lesson_date[2]),
                            )
                            lesson_day = week[str(lesson_date_splitted.weekday())]
                            logger.debug(
                                f"День недели занятия для пользователя с ID {user_id}: {lesson_day}"
                            )
                            lesson_time = (
                                f"{trial_lesson.get('time_from').split(' ')[1][:-3]}"
                            )
                            logger.debug(
                                f"У пользователя {user_in_db.phone_number} есть запланированные пробные занятия на {lesson_date, lesson_time} | {type(lesson_date)}."
                            )

                            lesson_day = week[str(lesson_date_splitted.weekday())]
                            logger.debug(
                                f"День недели занятия для пользователя с ID {user_id}: {lesson_day}"
                            )

                            lesson_time = f"{trial_lesson.get('time_from').split(' ')[1][:-3]} - {trial_lesson.get('time_to').split(' ')[1][:-3]}"
                            logger.debug(
                                f"Время занятия для пользователя с ID {user_id}: {lesson_time}"
                            )

                            # Получаем адрес занятия
                            lesson_address = str(trial_lesson.get("room_id", None))
                            logger.debug(
                                f"Адрес занятия для пользователя с ID {user_id}: {lesson_address}"
                            )

                            if lesson_address:
                                if lesson_address in MINSK:
                                    lesson_address = MINSK[lesson_address]
                                elif lesson_address in BORISOV:
                                    lesson_address = BORISOV[lesson_address]
                                elif lesson_address in BARANOVICHI:
                                    lesson_address = BARANOVICHI[lesson_address]
                                logger.debug(
                                    f"Адрес занятия для пользователя с ID {user_id} после обработки: {lesson_address}"
                                )

                            await callback.message.answer(
                                text=f"{user_crm_name} записан на пробный урок: \n{lesson_day}: {lesson_time}\n{lesson_address}"
                            )
                            logger.debug(
                                f"Отправлено расписание пользователю с ID {user_id}: {lesson_day}, {lesson_time}, {lesson_address}"
                            )
                        else:
                            await callback.message.answer(
                                text=f"У {user_crm_name} в настоящее время нет занятий."
                            )
                            logger.debug(
                                f"Пользователь с ID {user_id} не имеет запланированных занятий"
                            )
        await callback.answer()
        logger.debug(
            f"Обработка запроса на пробное занятие завершена для пользователя с ID {user_id}"
        )
    except Exception as e:
        logger.error(
            f"Ошибка при обработке запроса на пробное занятие от пользователя с ID {user_id}: {e}"
        )
        await callback.message.answer(
            "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
        )
        await callback.answer()

    logger.debug(
        f"Завершение обработки запроса на пробное занятие от пользователя с ID: {user_id}"
    )

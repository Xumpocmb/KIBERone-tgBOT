import hashlib
import hmac
from datetime import datetime

import requests
from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from logger_config import get_logger
from tg_bot.crm_logic.alfa_crm_api import find_user_by_phone, get_client_lessons, get_curr_tariff
from tg_bot.database.engine import session_maker
from tg_bot.database.orm_query import orm_get_user_by_tg_id
from tg_bot.keyboards.inline_keyboards.inline_back_to_main import back_to_main_inline
from tg_bot.middlewares.middleware_database import DataBaseSession

logger = get_logger()

erip_router: Router = Router()
erip_router.callback_query.middleware(DataBaseSession(session_pool=session_maker))

EXPRESS_PAY_TOKEN = "2666b84457dfef74f0f3d36d3d7c3e87"
EXPRESS_PAY_URL = "https://api.express-pay.by/v1/"
DEFAULT_PAY_URL = "https://client.express-pay.by/show?k=2F37583A-3ED1-453D-86FD-E3A13B7ADA19"


@erip_router.callback_query(F.data == "erip_payment")
async def process_button_erip_press(callback: CallbackQuery):
    logger.debug(f"Получен запрос на обработку кнопки 'erip_payment' от пользователя {callback.from_user.id}")

    formatted_text = """
    Как оплатить через систему «Расчет» (ЕРИП)?

    Вы можете оплатить счет через ЕРИП (без использования сканера) следующими способами:

    - интернет-банкинг,
    - в пункте банковского обслуживания,
    - на почте,
    - в инфокиоске,
    - в банкомате и т.д.

    Оплата возможна как наличными, так и картой, а также с использованием электронных денег. 

    Для проведения платежа необходимо:
    - выбрать пункт «Система «Расчет» (ЕРИП) → Сервис E-Pos (второй в дереве), → E-Pos оплата товаров и услуг.
    - номер плательщика можно не указывать, нажать продолжить.
    - ввести цифровой аналог QR-кода – это и есть номер счета: 19825-1-1
    - проверить корректность информации и ввести свои Фамилию Имя Отчество, указать сумму.
    - совершить платеж.

    Либо пройдя по ссылке
    https://client.express-pay.by/show?k=2F37583A-3ED1-453D-86FD-E3A13B7ADA19
    """

    try:
        await callback.message.answer(text=formatted_text, reply_markup=back_to_main_inline)
        logger.info(f"Отправлено сообщение пользователю {callback.from_user.id} с инструкциями по оплате через ЕРИП.")

        await callback.answer()
        logger.debug(f"Подтверждение нажатия кнопки отправлено пользователю {callback.from_user.id}.")
    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'erip_payment': {e}")


@erip_router.callback_query(F.data == "erip_payment-service")
async def process_button_erip_service(callback: CallbackQuery, session: AsyncSession):
    await callback.message.answer("Получаем данные...")
    await callback.answer()
    user = await orm_get_user_by_tg_id(session, callback.from_user.id)
    if user.phone_number:
        response = await find_user_by_phone(phone_number=user.phone_number)
        users_items = response.get("items", [])
        await callback.message.answer("Подготавливаем ссылку для оплаты. Это займёт не более 15 секунд... 😊")
        for item in users_items:
            result = await set_pay(item)
            if result:
                await callback.message.answer(result, reply_markup=back_to_main_inline)


async def set_pay(user_data):
    crm_id = user_data.get("id")

    await clear_user_not_paid_invoices(crm_id)
    amount_payable = await get_paid_summ(user_data, float(user_data.get("balance")), datetime.now().month)

    pay_url = (await get_pay_url(user_data.get("id"), round(amount_payable + 0.001, 2), user_data.get("name")))
    return (f"ФИО: {user_data.get("name").title()}\n"
            f"Сумма к оплате: {round(amount_payable + 0.001, 2)}\n"
            f"Ссылка для оплаты: {pay_url}")


async def get_signature(data):
    key = "Kiber".encode("utf-8")
    raw = data.encode("utf-8")

    digester = hmac.new(key, raw, hashlib.sha1)
    signature = digester.hexdigest()

    return signature.upper()


async def get_paid_summ(user_data, user_balance, curr_month):
    current_month = str(curr_month)
    if len(current_month) == 1:
        current_month = '0' + current_month
    lesson_price = round(await get_lesson_price(user_data.get("id"), user_data.get("branch_ids")[0], curr_month,
                                    datetime.now().year)+0.001, 2)
    taught_dates_dict, plan_dates_dict = await get_curr_month_lessons(user_data, current_month)
    if len(taught_dates_dict) + len(plan_dates_dict) == 0:
        if user_balance < 0:
            return abs(user_balance)
        else:
            return 0
    amount_payable = user_balance - lesson_price*len(plan_dates_dict)
    if amount_payable < 0:
        return abs(amount_payable)
    else:
        return await get_paid_summ(user_data, amount_payable, curr_month + 1)


async def get_curr_month_lessons(user_data, current_month):
    taught_lesson_dates = []
    plan_lesson_dates = []
    taught_lessons = await get_client_lessons(user_data.get("id"), [1], None, 3)
    taught_lessons = taught_lessons.get("items")
    plan_lessons = await get_client_lessons(user_data.get("id"), [1], None, 1)
    plan_lessons = plan_lessons.get("items")
    for lesson in taught_lessons:
        reason_id = lesson.get("details")[0].get("reason_id")
        if lesson.get("date").find('-' + current_month + '-') != -1 and reason_id != 1:
            taught_lesson_dates.append({"date": lesson.get("date"), "reason": reason_id})
    for lesson in plan_lessons:
        reason_id = lesson.get("details")[0].get("reason_id")
        if lesson.get("date").find('-' + current_month + '-') != -1 and reason_id != 1:
            plan_lesson_dates.append({"date": lesson.get("date"), "reason": reason_id})
    return taught_lesson_dates, plan_lesson_dates


async def get_lesson_price(user_crm_id, branch_id, current_month, current_year):
    tariff = await get_curr_tariff(user_crm_id, branch_id, current_month, current_year)
    return tariff.get("price") / 4


async def get_pay_url(crm_id, amount, name):
    url = EXPRESS_PAY_URL + "invoices?token=" + EXPRESS_PAY_TOKEN
    params = {
        "Token": EXPRESS_PAY_TOKEN,
        "AccountNo": str(crm_id),
        "Amount": str(amount),
        "Currency": "933",
        "Surname": str(name),
        "FirstName": "",
        "Patronymic": "",
        "IsNameEditable": "1",
        "IsAmountEditable": "0",
        "ReturnInvoiceUrl": "1",
    }

    data = ""
    for p in params.values():
        data += p

    params["signature"] = await get_signature(data)

    res = requests.post(url, data=params).json()

    return res.get("InvoiceUrl", DEFAULT_PAY_URL)


async def get_invoices(crm_id):
    url = EXPRESS_PAY_URL + "invoices"

    params = {
        "Token": EXPRESS_PAY_TOKEN,
        "AccountNo": crm_id,
        "Status": 1
    }

    data = ""
    for p in params.values():
        data += str(p)

    signature = await get_signature(data)
    params["signature"] = signature
    add_url = "?token=" + EXPRESS_PAY_TOKEN
    add_url += "&AccountNo=" + str(crm_id)
    add_url += "&Status=1&signature=" + signature

    return requests.get(url + add_url, data=params).json()


async def clear_user_not_paid_invoices(crm_id):
    url = EXPRESS_PAY_URL + "invoices"

    res = await get_invoices(crm_id)

    for inv in res.get("Items"):
        params = {
            "Token": EXPRESS_PAY_TOKEN,
            "InvoiceNo": inv.get("InvoiceNo")
        }
        data = ""
        for p in params.values():
            data += str(p)
        signature = await get_signature(data)
        params["signature"] = signature
        add_url = '/' + str(inv.get("InvoiceNo"))
        add_url += "?token=" + EXPRESS_PAY_TOKEN
        add_url += "&InvoiceNo=" + str(inv.get("InvoiceNo"))
        add_url += "&signature=" + signature
        requests.delete(url + add_url, data=params)

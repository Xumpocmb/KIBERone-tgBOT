from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery

from logger_config import get_logger
from tg_bot.keyboards.inline_keyboards.inline_back_to_main import back_to_main_inline

logger = get_logger()

erip_router: Router = Router()


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

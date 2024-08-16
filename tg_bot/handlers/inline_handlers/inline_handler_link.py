from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery
from tg_bot.keyboards.inline_keyboards.inline_keyboard_link import make_inline_link_kb

button_link_router: Router = Router()


# главное меню раздела Link


@button_link_router.callback_query(F.data == 'link')
async def process_button_link_press(callback: CallbackQuery):
    await callback.message.answer(text='Ссылки на наши социальные сети:',
                                  reply_markup = await make_inline_link_kb())
    await callback.message.delete()
    await callback.answer()













from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
)


# присылаем локации
def make_inline_contact_location_kb() -> InlineKeyboardMarkup:
    buttons = []
    # with Session(autoflush=False, bind=engine) as session:
    #     results = session.query(Manager).where(Manager.c.city == found_city.city)
    # for item in results:
    #     buttons.append(InlineKeyboardButton(text=item[2], callback_data=f'contact-location-{str(item[0])}'))
    buttons.append(InlineKeyboardButton(text='<< Назад', callback_data='inline_main'))
    buttons = [[button] for button in buttons]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons, resize_keyboard=True,
                                    input_field_placeholder="Выберите действие..")
    return keyboard

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Пользователи"), KeyboardButton(text="Активные подписки")],
            [KeyboardButton(text="Доход"), KeyboardButton(text="Рассылка сообщений")],
            [KeyboardButton(text="Выдать VPN вручную"), KeyboardButton(text="Заблокировать пользователя")],
        ],
        resize_keyboard=True,
    )

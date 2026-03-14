from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Купить VPN"), KeyboardButton(text="Пробный период")],
            [KeyboardButton(text="Моя подписка"), KeyboardButton(text="Мой VPN")],
            [KeyboardButton(text="Поддержка")],
        ],
        resize_keyboard=True,
    )


def plans_keyboard() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="1 месяц — 200 ₽", callback_data="buy:plan_1m")
    kb.button(text="3 месяца — 500 ₽", callback_data="buy:plan_3m")
    kb.button(text="12 месяцев — 1200 ₽", callback_data="buy:plan_12m")
    kb.adjust(1)
    return kb


def payment_keyboard(invoice_id: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="Проверить оплату", callback_data=f"paycheck:{invoice_id}")
    kb.adjust(1)
    return kb

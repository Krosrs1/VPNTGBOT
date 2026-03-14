from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import Database
from keyboards.menu import main_menu_keyboard

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, db: Database) -> None:
    """Register user in DB and show main user menu."""
    db.ensure_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "Добро пожаловать в VPN Bot! Выберите действие в меню ниже.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(lambda msg: msg.text == "Поддержка")
async def support(message: Message) -> None:
    await message.answer(
        "Поддержка: @your_support\n"
        "Если есть проблема с оплатой или подключением — напишите нам."
    )

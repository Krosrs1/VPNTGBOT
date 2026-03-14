from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Router
from aiogram.types import Message

from database import Database

router = Router()


@router.message(lambda msg: msg.text == "Моя подписка")
async def my_subscription(message: Message, db: Database) -> None:
    user = db.get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("Пользователь не найден. Нажмите /start")
        return

    sub = db.get_latest_subscription(int(user["id"]))
    if not sub:
        await message.answer("У вас пока нет подписки.")
        return

    expire = datetime.fromisoformat(sub.expire_date)
    days_left = max((expire - datetime.now(timezone.utc)).days, 0)
    await message.answer(
        "📄 Ваша подписка:\n"
        f"Тариф: {sub.plan}\n"
        f"Действует до: {expire:%Y-%m-%d %H:%M UTC}\n"
        f"Осталось дней: {days_left}\n\n"
        "Чтобы продлить подписку, нажмите «Купить VPN» и выберите тариф."
    )

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.types import Message

from config import TRIAL_HOURS, TRIAL_TRAFFIC_GB
from database import Database
from marzban_api import MarzbanAPI, MarzbanAPIError

router = Router()


@router.message(lambda msg: msg.text == "Пробный период")
async def trial_period(message: Message, db: Database, marzban: MarzbanAPI) -> None:
    user = db.get_user_by_tg(message.from_user.id)
    if not user:
        db.ensure_user(message.from_user.id, message.from_user.username)
        user = db.get_user_by_tg(message.from_user.id)
        if not user:
            await message.answer("Ошибка регистрации пользователя. Попробуйте позже.")
            return

    if int(user["trial_used"]) == 1:
        await message.answer("Вы уже использовали пробный период.")
        return

    expire_at = datetime.now(timezone.utc) + timedelta(hours=TRIAL_HOURS)
    username = MarzbanAPI.generate_username(message.from_user.id)
    limit = TRIAL_TRAFFIC_GB * 1024 * 1024 * 1024

    try:
        created = await marzban.create_user(username=username, expire_at=expire_at, data_limit_bytes=limit)
    except MarzbanAPIError as exc:
        await message.answer(f"Не удалось активировать пробный период: {exc}")
        return

    db.set_trial_used(int(user["id"]))
    db.upsert_subscription(
        user_id=int(user["id"]),
        marzban_username=username,
        plan="trial",
        expire_date=expire_at.isoformat(),
    )

    links = created.get("links") or []
    vpn_link = links[0] if links else "Ссылка не получена."

    await message.answer(
        "🎁 Пробный период активирован!\n"
        f"Срок: {TRIAL_HOURS} часов\n"
        f"Трафик: {TRIAL_TRAFFIC_GB} GB\n"
        f"VPN ссылка:\n{vpn_link}"
    )

from aiogram import Router
from aiogram.types import Message

from database import Database
from marzban_api import MarzbanAPI, MarzbanAPIError

router = Router()


@router.message(lambda msg: msg.text == "Мой VPN")
async def my_vpn(message: Message, db: Database, marzban: MarzbanAPI) -> None:
    user = db.get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("Пользователь не найден. Нажмите /start")
        return

    sub = db.get_latest_subscription(int(user["id"]))
    if not sub:
        await message.answer("У вас пока нет VPN. Оформите подписку через «Купить VPN».")
        return

    try:
        marz_user = await marzban.get_user(sub.marzban_username)
    except MarzbanAPIError as exc:
        await message.answer(f"Ошибка получения конфигурации: {exc}")
        return

    links = marz_user.get("links") or []
    vpn_link = links[0] if links else "Ссылка недоступна"

    await message.answer(
        "🔐 Ваш VPN:\n"
        f"Username: {sub.marzban_username}\n"
        f"VPN ссылка: {vpn_link}\n\n"
        "Инструкция:\n"
        "1) Установите клиент Hiddify или v2rayN.\n"
        "2) Импортируйте ссылку подключения.\n"
        "3) Подключитесь к серверу."
    )

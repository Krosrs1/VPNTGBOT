from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from config import Settings
from database import Database
from keyboards.admin import admin_menu_keyboard
from marzban_api import MarzbanAPI, MarzbanAPIError

router = Router()


class AdminStates(StatesGroup):
    waiting_broadcast_text = State()
    waiting_manual_grant = State()
    waiting_block_username = State()


def _is_admin(message: Message, settings: Settings) -> bool:
    return message.from_user and message.from_user.id == settings.admin_id


@router.message(Command("admin"))
async def admin_entry(message: Message, settings: Settings) -> None:
    if not _is_admin(message, settings):
        await message.answer("Доступ запрещен")
        return

    await message.answer("Админ-панель", reply_markup=admin_menu_keyboard())


@router.message(lambda m: m.text == "Пользователи")
async def users_stat(message: Message, db: Database, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    await message.answer(
        f"Всего пользователей: {db.get_user_count()}\n"
        f"Пользователи с trial: {db.get_trial_count()}"
    )


@router.message(lambda m: m.text == "Активные подписки")
async def active_subs(message: Message, db: Database, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    await message.answer(f"Активные подписки: {db.get_active_subscriptions_count()}")


@router.message(lambda m: m.text == "Доход")
async def income(message: Message, db: Database, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    await message.answer(f"Общий доход: {db.get_total_income():.2f} ₽")


@router.message(lambda m: m.text == "Рассылка сообщений")
async def broadcast_start(message: Message, state: FSMContext, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    await state.set_state(AdminStates.waiting_broadcast_text)
    await message.answer("Введите текст рассылки:")


@router.message(AdminStates.waiting_broadcast_text)
async def broadcast_send(message: Message, state: FSMContext, db: Database, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return

    sent = 0
    for tg_id in db.list_user_telegram_ids():
        try:
            await message.bot.send_message(tg_id, f"📢 Сообщение от администрации:\n\n{message.text}")
            sent += 1
        except Exception:
            continue

    await state.clear()
    await message.answer(f"Рассылка завершена. Доставлено: {sent}")


@router.message(lambda m: m.text == "Выдать VPN вручную")
async def manual_grant_start(message: Message, state: FSMContext, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    await state.set_state(AdminStates.waiting_manual_grant)
    await message.answer("Формат: telegram_id дни_доступа (пример: 123456789 30)")


@router.message(AdminStates.waiting_manual_grant)
async def manual_grant(
    message: Message,
    state: FSMContext,
    db: Database,
    marzban: MarzbanAPI,
    settings: Settings,
) -> None:
    if not _is_admin(message, settings):
        return

    try:
        tg_id_raw, days_raw = message.text.split()
        tg_id, days = int(tg_id_raw), int(days_raw)
    except Exception:
        await message.answer("Неверный формат. Пример: 123456789 30")
        return

    user = db.get_user_by_tg(tg_id)
    if not user:
        await message.answer("Пользователь не найден в базе (должен нажать /start).")
        return

    expire = datetime.now(timezone.utc) + timedelta(days=days)
    sub = db.get_latest_subscription(int(user["id"]))

    try:
        if sub:
            username = sub.marzban_username
            await marzban.extend_user(username, expire)
        else:
            username = MarzbanAPI.generate_username(tg_id)
            await marzban.create_user(username, expire)

        db.upsert_subscription(int(user["id"]), username, f"manual_{days}d", expire.isoformat())
    except MarzbanAPIError as exc:
        await message.answer(f"Ошибка выдачи VPN: {exc}")
        return

    await state.clear()
    await message.answer(f"Готово. Пользователь {tg_id} активен до {expire:%Y-%m-%d %H:%M UTC}")


@router.message(lambda m: m.text == "Заблокировать пользователя")
async def block_start(message: Message, state: FSMContext, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    await state.set_state(AdminStates.waiting_block_username)
    await message.answer("Введите marzban username для блокировки:")


@router.message(AdminStates.waiting_block_username)
async def block_user(
    message: Message,
    state: FSMContext,
    marzban: MarzbanAPI,
    settings: Settings,
) -> None:
    if not _is_admin(message, settings):
        return

    username = message.text.strip()
    try:
        await marzban.delete_user(username)
    except MarzbanAPIError as exc:
        await message.answer(f"Ошибка блокировки: {exc}")
        return

    await state.clear()
    await message.answer(f"Пользователь {username} удален/заблокирован в Marzban.")

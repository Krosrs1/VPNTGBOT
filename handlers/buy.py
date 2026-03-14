from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from config import PLANS
from cryptobot_api import CryptoBotAPI, CryptoBotError
from database import Database
from keyboards.menu import payment_keyboard, plans_keyboard
from marzban_api import MarzbanAPI, MarzbanAPIError

router = Router()


def _months_to_timedelta(months: int) -> timedelta:
    # Средняя длина месяца в днях подходит для подписок без календарных усложнений.
    return timedelta(days=30 * months)


@router.message(lambda msg: msg.text == "Купить VPN")
async def buy_menu(message: Message) -> None:
    await message.answer("Выберите тариф:", reply_markup=plans_keyboard().as_markup())


@router.callback_query(lambda c: c.data and c.data.startswith("buy:"))
async def create_invoice(
    callback: CallbackQuery,
    db: Database,
    crypto: CryptoBotAPI,
) -> None:
    plan_key = callback.data.split(":", 1)[1]
    if plan_key not in PLANS:
        await callback.answer("Неизвестный тариф", show_alert=True)
        return

    user_id = db.ensure_user(callback.from_user.id, callback.from_user.username)
    plan = PLANS[plan_key]

    try:
        invoice = await crypto.create_invoice(
            amount=float(plan["price_rub"]),
            description=f"VPN подписка ({plan_key})",
            payload=f"{callback.from_user.id}:{plan_key}",
        )
    except CryptoBotError as exc:
        await callback.message.answer(f"Ошибка создания счета: {exc}")
        await callback.answer()
        return

    invoice_id = int(invoice["invoice_id"])
    db.create_payment(
        user_id=user_id,
        invoice_id=invoice_id,
        plan=plan_key,
        amount=float(plan["price_rub"]),
        status="active",
    )

    await callback.message.answer(
        f"Счет создан: {invoice['pay_url']}\n"
        f"Тариф: {plan_key}\n"
        "После оплаты нажмите «Проверить оплату».",
        reply_markup=payment_keyboard(invoice_id).as_markup(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("paycheck:"))
async def check_payment(
    callback: CallbackQuery,
    db: Database,
    crypto: CryptoBotAPI,
    marzban: MarzbanAPI,
) -> None:
    invoice_id = int(callback.data.split(":", 1)[1])

    payment = db.get_payment(invoice_id)
    if not payment:
        await callback.answer("Платеж не найден", show_alert=True)
        return

    user_row = db.get_user_by_tg(callback.from_user.id)
    if not user_row:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    if int(payment["user_id"]) != int(user_row["id"]):
        await callback.answer("Это не ваш счет", show_alert=True)
        return

    # Идемпотентность выдачи: если уже обработано — повторно не продлеваем.
    if int(payment["is_processed"]) == 1 and str(payment["status"]) == "paid":
        await callback.answer("Оплата уже обработана ранее", show_alert=True)
        return

    try:
        invoice = await crypto.get_invoice(invoice_id)
    except CryptoBotError as exc:
        await callback.message.answer(f"Не удалось проверить счет: {exc}")
        await callback.answer()
        return

    status = str(invoice.get("status", "unknown"))
    db.update_payment_status(invoice_id, status)

    if status != "paid":
        await callback.answer("Оплата еще не подтверждена", show_alert=True)
        return

    # payload дополнительно проверяем, но источник тарифа берем из БД,
    # чтобы избежать зависимости от внешнего payload.
    payload = str(invoice.get("payload", ""))
    try:
        tg_id_raw, _ = payload.split(":", 1)
        if int(tg_id_raw) != callback.from_user.id:
            await callback.answer("Счет не принадлежит текущему пользователю", show_alert=True)
            return
    except Exception:
        await callback.answer("Некорректный payload счета", show_alert=True)
        return

    plan_key = str(payment["plan"])
    if plan_key not in PLANS:
        await callback.answer("Неизвестный тариф в платеже", show_alert=True)
        return

    sub = db.get_latest_subscription(int(user_row["id"]))
    now = datetime.now(timezone.utc)
    months = int(PLANS[plan_key]["months"])

    try:
        if sub:
            current_expire = datetime.fromisoformat(sub.expire_date)
            new_expire = max(current_expire, now) + _months_to_timedelta(months)
            marzban_username = sub.marzban_username
            marz_user = await marzban.extend_user(marzban_username, new_expire)
        else:
            new_expire = now + _months_to_timedelta(months)
            marzban_username = MarzbanAPI.generate_username(callback.from_user.id)
            marz_user = await marzban.create_user(marzban_username, new_expire)

        db.upsert_subscription(
            user_id=int(user_row["id"]),
            marzban_username=marzban_username,
            plan=plan_key,
            expire_date=new_expire.isoformat(),
        )
        db.mark_payment_processed(invoice_id)
    except MarzbanAPIError as exc:
        await callback.message.answer(f"Оплата прошла, но ошибка выдачи VPN: {exc}")
        await callback.answer()
        return

    links = marz_user.get("links") or []
    vpn_link = links[0] if links else "Ссылка не получена. Проверьте панель Marzban."

    await callback.message.answer(
        "✅ Оплата подтверждена!\n"
        f"Подписка активна до: {new_expire:%Y-%m-%d %H:%M UTC}\n"
        f"VPN ссылка:\n{vpn_link}"
    )
    await callback.answer("Оплата подтверждена")

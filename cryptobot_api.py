from __future__ import annotations

import httpx


class CryptoBotError(RuntimeError):
    pass


class CryptoBotAPI:
    """Async wrapper around CryptoBot pay API."""

    def __init__(self, token: str) -> None:
        self.base_url = "https://pay.crypt.bot/api"
        self.headers = {"Crypto-Pay-API-Token": token}

    async def create_invoice(self, amount: float, description: str, payload: str) -> dict:
        # Выставляем счет в RUB, а пользователь может оплатить поддерживаемыми активами.
        request_payload = {
            "currency_type": "fiat",
            "fiat": "RUB",
            "amount": f"{amount:.2f}",
            "description": description,
            "payload": payload,
            "accepted_assets": "USDT,TON,BTC,ETH",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.base_url}/createInvoice",
                headers=self.headers,
                json=request_payload,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise CryptoBotError(f"Invalid JSON from createInvoice: {response.text}") from exc

        if response.status_code >= 400 or not data.get("ok"):
            raise CryptoBotError(f"Failed to create invoice: {data}")
        return data["result"]

    async def get_invoice(self, invoice_id: int) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.base_url}/getInvoices",
                headers=self.headers,
                params={"invoice_ids": str(invoice_id)},
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise CryptoBotError(f"Invalid JSON from getInvoices: {response.text}") from exc

        if response.status_code >= 400 or not data.get("ok"):
            raise CryptoBotError(f"Failed to read invoice: {data}")
        items = data["result"].get("items", [])
        if not items:
            raise CryptoBotError("Invoice not found")
        return items[0]

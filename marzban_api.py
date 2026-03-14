from __future__ import annotations

from datetime import datetime, timezone
import secrets
import string

import httpx


class MarzbanAPIError(RuntimeError):
    pass


class MarzbanAPI:
    """Small async client for Marzban panel."""

    def __init__(self, base_url: str, token: str, inbound_tag: str = "VLESS TCP REALITY") -> None:
        self.base_url = base_url.rstrip("/")
        self.inbound_tag = inbound_tag
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def create_user(
        self,
        username: str,
        expire_at: datetime,
        data_limit_bytes: int | None = None,
    ) -> dict:
        payload: dict = {
            "username": username,
            "proxies": {"vless": {}},
            "inbounds": {"vless": [self.inbound_tag]},
            "expire": int(expire_at.replace(tzinfo=timezone.utc).timestamp()),
        }
        if data_limit_bytes is not None:
            payload["data_limit"] = data_limit_bytes

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.base_url}/api/user", headers=self.headers, json=payload
            )

        if response.status_code >= 400:
            raise MarzbanAPIError(f"Failed to create user: {response.text}")

        try:
            return response.json()
        except ValueError as exc:
            raise MarzbanAPIError(f"Invalid JSON from Marzban create_user: {response.text}") from exc

    async def get_user(self, username: str) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.base_url}/api/user/{username}", headers=self.headers
            )

        if response.status_code >= 400:
            raise MarzbanAPIError(f"Failed to get user: {response.text}")

        try:
            return response.json()
        except ValueError as exc:
            raise MarzbanAPIError(f"Invalid JSON from Marzban get_user: {response.text}") from exc

    async def delete_user(self, username: str) -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.delete(
                f"{self.base_url}/api/user/{username}", headers=self.headers
            )
        if response.status_code >= 400:
            raise MarzbanAPIError(f"Failed to delete user: {response.text}")

    async def extend_user(self, username: str, expire_at: datetime) -> dict:
        user = await self.get_user(username)
        user["expire"] = int(expire_at.replace(tzinfo=timezone.utc).timestamp())

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.put(
                f"{self.base_url}/api/user/{username}", headers=self.headers, json=user
            )

        if response.status_code >= 400:
            raise MarzbanAPIError(f"Failed to extend user: {response.text}")

        try:
            return response.json()
        except ValueError as exc:
            raise MarzbanAPIError(f"Invalid JSON from Marzban extend_user: {response.text}") from exc

    @staticmethod
    def generate_username(telegram_id: int) -> str:
        suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))
        return f"tg_{telegram_id}_{suffix}"[:32]

from __future__ import annotations

import asyncio
import logging

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import TelegramObject

from config import Settings, load_settings
from cryptobot_api import CryptoBotAPI
from database import Database
from handlers import admin, buy, profile, start, trial, vpn
from marzban_api import MarzbanAPI


class DependenciesMiddleware(BaseMiddleware):
    """Inject singleton service objects into aiogram handler kwargs."""

    def __init__(
        self,
        settings: Settings,
        db: Database,
        marzban: MarzbanAPI,
        crypto: CryptoBotAPI,
    ) -> None:
        self.settings = settings
        self.db = db
        self.marzban = marzban
        self.crypto = crypto

    async def __call__(self, handler, event: TelegramObject, data: dict):
        data["settings"] = self.settings
        data["db"] = self.db
        data["marzban"] = self.marzban
        data["crypto"] = self.crypto
        return await handler(event, data)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = load_settings()
    db = Database(settings.database_path)
    db.init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    deps = DependenciesMiddleware(
        settings=settings,
        db=db,
        marzban=MarzbanAPI(
            base_url=settings.marzban_url,
            token=settings.marzban_token,
            inbound_tag=settings.marzban_inbound_tag,
        ),
        crypto=CryptoBotAPI(settings.cryptobot_token),
    )
    dp.message.middleware(deps)
    dp.callback_query.middleware(deps)

    dp.include_router(start.router)
    dp.include_router(buy.router)
    dp.include_router(trial.router)
    dp.include_router(profile.router)
    dp.include_router(vpn.router)
    dp.include_router(admin.router)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

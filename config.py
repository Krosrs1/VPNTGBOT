from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import os
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_id: int
    marzban_url: str
    marzban_token: str
    cryptobot_token: str
    marzban_inbound_tag: str = "VLESS TCP REALITY"
    database_path: str = "vpn_bot.db"


def load_settings() -> Settings:
    """Load and validate environment settings for the bot."""
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_id_raw = os.getenv("ADMIN_ID", "").strip()
    marzban_url = os.getenv("MARZBAN_URL", "").rstrip("/")
    marzban_token = os.getenv("MARZBAN_TOKEN", "").strip()
    cryptobot_token = os.getenv("CRYPTOBOT_TOKEN", "").strip()
    marzban_inbound_tag = os.getenv("MARZBAN_INBOUND_TAG", "VLESS TCP REALITY").strip()
    database_path = os.getenv("DATABASE_PATH", "vpn_bot.db").strip() or "vpn_bot.db"

    missing = [
        name
        for name, value in {
            "BOT_TOKEN": bot_token,
            "ADMIN_ID": admin_id_raw,
            "MARZBAN_URL": marzban_url,
            "MARZBAN_TOKEN": marzban_token,
            "CRYPTOBOT_TOKEN": cryptobot_token,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    try:
        admin_id = int(admin_id_raw)
    except ValueError as exc:
        raise ValueError("ADMIN_ID must be an integer") from exc

    return Settings(
        bot_token=bot_token,
        admin_id=admin_id,
        marzban_url=marzban_url,
        marzban_token=marzban_token,
        cryptobot_token=cryptobot_token,
        marzban_inbound_tag=marzban_inbound_tag,
        database_path=database_path,
    )


PLANS: Final[dict[str, dict[str, int | float]]] = {
    "plan_1m": {"months": 1, "price_rub": 200.0},
    "plan_3m": {"months": 3, "price_rub": 500.0},
    "plan_12m": {"months": 12, "price_rub": 1200.0},
}

TRIAL_HOURS: Final[int] = 24
TRIAL_TRAFFIC_GB: Final[int] = 5

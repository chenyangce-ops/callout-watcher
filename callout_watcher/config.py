from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Account:
    username: str
    display_name: str | None = None


@dataclass(frozen=True)
class ClassificationConfig:
    openai_model: str = "gpt-4o-mini"
    confidence_threshold: float = 0.72
    include_replies: bool = False
    include_retweets: bool = False
    bullish_keywords: tuple[str, ...] = ()
    asset_keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class TelegramConfig:
    bot_token_env: str = "TELEGRAM_BOT_TOKEN"
    chat_id_env: str = "TELEGRAM_CHAT_ID"


@dataclass(frozen=True)
class DiscordConfig:
    webhook_url_env: str = "DISCORD_WEBHOOK_URL"


@dataclass(frozen=True)
class NotificationConfig:
    channel: str = "console"
    telegram: TelegramConfig = TelegramConfig()
    discord: DiscordConfig = DiscordConfig()


@dataclass(frozen=True)
class AppConfig:
    poll_interval_seconds: int
    accounts: tuple[Account, ...]
    classification: ClassificationConfig
    notifications: NotificationConfig


def load_config(path: str | Path) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    accounts = tuple(
        Account(username=str(item["username"]).lstrip("@"), display_name=item.get("display_name"))
        for item in raw.get("accounts", [])
    )
    if not accounts:
        raise ValueError("config must include at least one account")

    classification_raw: dict[str, Any] = raw.get("classification", {})
    notifications_raw: dict[str, Any] = raw.get("notifications", {})
    telegram_raw: dict[str, Any] = notifications_raw.get("telegram", {})
    discord_raw: dict[str, Any] = notifications_raw.get("discord", {})

    return AppConfig(
        poll_interval_seconds=int(raw.get("poll_interval_seconds", 120)),
        accounts=accounts,
        classification=ClassificationConfig(
            openai_model=str(classification_raw.get("openai_model", "gpt-4o-mini")),
            confidence_threshold=float(classification_raw.get("confidence_threshold", 0.72)),
            include_replies=bool(classification_raw.get("include_replies", False)),
            include_retweets=bool(classification_raw.get("include_retweets", False)),
            bullish_keywords=tuple(classification_raw.get("bullish_keywords", [])),
            asset_keywords=tuple(classification_raw.get("asset_keywords", [])),
        ),
        notifications=NotificationConfig(
            channel=str(notifications_raw.get("channel", "console")).lower(),
            telegram=TelegramConfig(
                bot_token_env=str(telegram_raw.get("bot_token_env", "TELEGRAM_BOT_TOKEN")),
                chat_id_env=str(telegram_raw.get("chat_id_env", "TELEGRAM_CHAT_ID")),
            ),
            discord=DiscordConfig(
                webhook_url_env=str(discord_raw.get("webhook_url_env", "DISCORD_WEBHOOK_URL")),
            ),
        ),
    )

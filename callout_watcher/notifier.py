from __future__ import annotations

import os
from dataclasses import dataclass

import requests

from .classifier import Classification
from .config import NotificationConfig
from .x_client import Post


@dataclass(frozen=True)
class Alert:
    post: Post
    classification: Classification

    def format(self) -> str:
        parts = [
            "发现疑似喊单",
            f"账号: @{self.post.username}",
            f"时间: {self.post.created_at.isoformat()}",
            f"置信度: {self.classification.confidence:.2f}",
        ]
        if self.classification.asset:
            parts.append(f"标的: {self.classification.asset}")
        if self.classification.side:
            parts.append(f"方向: {self.classification.side}")
        parts.extend(
            [
                f"原因: {self.classification.reason}",
                "",
                self.post.text,
                "",
                self.post.url,
            ]
        )
        return "\n".join(parts)


class Notifier:
    def __init__(self, config: NotificationConfig) -> None:
        self.config = config

    def send(self, alert: Alert) -> None:
        if self.config.channel == "telegram":
            self._send_telegram(alert.format())
            return
        if self.config.channel == "discord":
            self._send_discord(alert.format())
            return
        print(alert.format(), flush=True)

    def _send_telegram(self, message: str) -> None:
        token = os.environ[self.config.telegram.bot_token_env]
        chat_id = os.environ[self.config.telegram.chat_id_env]
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "disable_web_page_preview": False},
            timeout=20,
        )
        response.raise_for_status()

    def _send_discord(self, message: str) -> None:
        webhook_url = os.environ[self.config.discord.webhook_url_env]
        response = requests.post(webhook_url, json={"content": message}, timeout=20)
        response.raise_for_status()

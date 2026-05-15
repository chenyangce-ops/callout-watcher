from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from openai import OpenAI

from .config import ClassificationConfig


@dataclass(frozen=True)
class Classification:
    is_callout: bool
    confidence: float
    reason: str
    asset: str | None = None
    side: str | None = None


class CalloutClassifier:
    def __init__(self, config: ClassificationConfig) -> None:
        self.config = config
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None

    def classify(self, text: str) -> Classification:
        if self.client:
            try:
                result = self._classify_with_openai(text)
                if result.confidence >= self.config.confidence_threshold or not result.is_callout:
                    return result
            except Exception as exc:
                fallback = self._classify_with_rules(text)
                return Classification(
                    is_callout=fallback.is_callout,
                    confidence=fallback.confidence,
                    reason=f"OpenAI 分类失败，已用规则判断: {exc.__class__.__name__}; {fallback.reason}",
                    asset=fallback.asset,
                    side=fallback.side,
                )
        return self._classify_with_rules(text)

    def _classify_with_rules(self, text: str) -> Classification:
        normalized = text.lower()
        action_hits = [word for word in self.config.bullish_keywords if word.lower() in normalized]
        asset_hits = self._asset_hits(text)
        price_or_percent = bool(re.search(r"(\$?\d+(?:\.\d+)?\s?k?\b|\d+(?:\.\d+)?%)", text, re.I))
        imperative = bool(re.search(r"(buy|long|short|entry|入|买|冲|开多|开空|上车|埋伏)", normalized, re.I))
        score = 0.0
        score += 0.35 if action_hits else 0
        score += 0.3 if asset_hits else 0
        score += 0.2 if price_or_percent else 0
        score += 0.15 if imperative else 0
        is_callout = score >= self.config.confidence_threshold
        reason = "命中交易动作/资产/价格等规则" if is_callout else "没有足够交易指令特征"
        return Classification(
            is_callout=is_callout,
            confidence=round(score, 2),
            reason=reason,
            asset=asset_hits[0] if asset_hits else None,
            side=self._side(normalized),
        )

    def _classify_with_openai(self, text: str) -> Classification:
        response = self.client.responses.create(
            model=self.config.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "你是加密货币推文分类器。判断帖子是否像交易喊单。"
                        "喊单是指明确或半明确建议买入、卖出、做多、做空、入场、止盈、止损、目标价、仓位或跟单。"
                        "纯新闻、复盘、观点、meme、免责声明不足以算喊单。"
                        "只输出 JSON。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "请输出字段: is_callout(boolean), confidence(0-1), reason(string), "
                        f"asset(string|null), side(long|short|buy|sell|null)。帖子:\n{text}"
                    ),
                },
            ],
            text={"format": {"type": "json_object"}},
        )
        payload = json.loads(response.output_text)
        return Classification(
            is_callout=bool(payload.get("is_callout")),
            confidence=float(payload.get("confidence", 0)),
            reason=str(payload.get("reason", "")),
            asset=payload.get("asset"),
            side=payload.get("side"),
        )

    def _asset_hits(self, text: str) -> list[str]:
        hits = []
        for keyword in self.config.asset_keywords:
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])", text, re.I):
                hits.append(keyword)
        cashtags = re.findall(r"\$[A-Z][A-Z0-9]{1,9}\b", text)
        return hits + cashtags

    @staticmethod
    def _side(normalized: str) -> str | None:
        if any(word in normalized for word in ("short", "开空", "做空", "空")):
            return "short"
        if any(word in normalized for word in ("long", "buy", "开多", "做多", "买", "上车")):
            return "long"
        if any(word in normalized for word in ("sell", "卖", "减仓", "清仓")):
            return "sell"
        return None

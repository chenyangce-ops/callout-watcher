from callout_watcher.classifier import CalloutClassifier
from callout_watcher.config import ClassificationConfig


def make_classifier() -> CalloutClassifier:
    return CalloutClassifier(
        ClassificationConfig(
            confidence_threshold=0.72,
            bullish_keywords=("buy", "long", "entry", "target", "买入", "开多", "目标", "止损"),
            asset_keywords=("BTC", "ETH", "SOL"),
        )
    )


def test_detects_callout() -> None:
    result = make_classifier().classify("BTC long entry 65000 target 68000 stop loss 64000")

    assert result.is_callout is True
    assert result.asset == "BTC"
    assert result.side == "long"


def test_ignores_market_commentary() -> None:
    result = make_classifier().classify("BTC volatility is high today, watching the weekly close.")

    assert result.is_callout is False

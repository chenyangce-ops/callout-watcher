from datetime import datetime, timezone

from callout_watcher.analyze_history import render_markdown
from callout_watcher.classifier import Classification
from callout_watcher.x_client import Post


def test_render_markdown_summary() -> None:
    post = Post(
        id="1",
        username="WallStreet0Name",
        text="BTC long entry 65000 target 68000",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        url="https://x.com/WallStreet0Name/status/1",
    )
    result = Classification(True, 0.9, "matched", "BTC", "long")

    report = render_markdown("WallStreet0Name", [(post, result)], max_pages=1)

    assert "分析推文数: 1" in report
    assert "疑似喊单数: 1" in report
    assert "BTC: 1" in report

from pathlib import Path

from callout_watcher.config import load_config


def test_load_stock_search_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
poll_interval_seconds: 86400
accounts:
  - username: WallStreet0Name
classification: {}
notifications:
  channel: console
stock_search:
  enabled: true
  max_results: 25
  exclude_replies: true
  exclude_retweets: true
  keywords:
    - 美股
    - NVDA
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.stock_search.enabled is True
    assert config.stock_search.max_results == 25
    assert config.stock_search.keywords == ("美股", "NVDA")

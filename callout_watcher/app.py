from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from .classifier import CalloutClassifier
from .config import load_config
from .notifier import Alert, Notifier
from .state import StateStore
from .x_client import XClient


LOGGER = logging.getLogger("callout_watcher")


def run_once(config_path: Path, state_path: Path) -> None:
    load_dotenv()
    config = load_config(config_path)
    bearer_token = os.environ.get("X_BEARER_TOKEN")
    if not bearer_token:
        raise RuntimeError("X_BEARER_TOKEN is required")

    x_client = XClient(bearer_token)
    state = StateStore(state_path)
    classifier = CalloutClassifier(config.classification)
    notifier = Notifier(config.notifications)

    for account in config.accounts:
        username = account.username
        since_id = state.get_since_id(username)
        if config.stock_search.enabled:
            posts = x_client.search_recent_posts(
                username=username,
                keywords=config.stock_search.keywords,
                since_id=since_id,
                max_results=config.stock_search.max_results,
                exclude_replies=config.stock_search.exclude_replies,
                exclude_retweets=config.stock_search.exclude_retweets,
            )
            LOGGER.info("searched %s stock-related posts for @%s", len(posts), username)
        else:
            user_id = x_client.get_user_id(username)
            posts = x_client.get_latest_posts(
                username=username,
                user_id=user_id,
                since_id=since_id,
                include_replies=config.classification.include_replies,
                include_retweets=config.classification.include_retweets,
            )
            LOGGER.info("fetched %s posts for @%s", len(posts), username)
        for post in posts:
            result = classifier.classify(post.text)
            if result.is_callout:
                notifier.send(Alert(post=post, classification=result))
            state.set_since_id(username, post.id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch X accounts and alert on trading callouts.")
    parser.add_argument("--config", default="config.yaml", type=Path)
    parser.add_argument("--state", default=".data/state.json", type=Path)
    parser.add_argument("--once", action="store_true", help="Run one polling pass and exit.")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(message)s")
    config = load_config(args.config)

    while True:
        run_once(args.config, args.state)
        if args.once:
            break
        time.sleep(config.poll_interval_seconds)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

from .classifier import CalloutClassifier, Classification
from .config import load_config
from .x_client import Post, XClient


def analyze_history(
    config_path: Path,
    username: str,
    output_path: Path,
    max_pages: int,
    max_posts: int | None,
    json_output_path: Path | None = None,
) -> None:
    load_dotenv()
    config = load_config(config_path)
    bearer_token = os.environ.get("X_BEARER_TOKEN")
    if not bearer_token:
        raise RuntimeError("X_BEARER_TOKEN is required")

    x_client = XClient(bearer_token)
    classifier = CalloutClassifier(config.classification)
    user_id = x_client.get_user_id(username)
    posts = x_client.get_post_history(
        username=username,
        user_id=user_id,
        include_replies=config.classification.include_replies,
        include_retweets=config.classification.include_retweets,
        max_pages=max_pages,
        max_posts=max_posts,
    )

    rows = [(post, classifier.classify(post.text)) for post in posts]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(username, rows, max_pages), encoding="utf-8")

    if json_output_path:
        json_output_path.parent.mkdir(parents=True, exist_ok=True)
        json_output_path.write_text(
            json.dumps(
                [
                    {
                        "post": {
                            **asdict(post),
                            "created_at": post.created_at.isoformat(),
                        },
                        "classification": asdict(result),
                    }
                    for post, result in rows
                ],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )


def render_markdown(username: str, rows: list[tuple[Post, Classification]], max_pages: int) -> str:
    callouts = [(post, result) for post, result in rows if result.is_callout]
    assets = Counter(result.asset for _, result in callouts if result.asset)
    sides = Counter(result.side for _, result in callouts if result.side)
    total = len(rows)
    rate = (len(callouts) / total * 100) if total else 0

    lines = [
        f"# @{username} 历史推文喊单分析",
        "",
        "## 摘要",
        "",
        f"- 分析推文数: {total}",
        f"- 疑似喊单数: {len(callouts)}",
        f"- 疑似喊单比例: {rate:.1f}%",
        f"- 最大分页数: {max_pages}",
        "",
        "说明：X API 是否能返回完整历史取决于账号权限和接口限制；本报告分析的是本次接口实际返回的数据。",
        "",
        "## 高频标的",
        "",
    ]
    lines.extend(_counter_lines(assets))
    lines.extend(["", "## 方向分布", ""])
    lines.extend(_counter_lines(sides))
    lines.extend(["", "## 疑似喊单明细", ""])

    if not callouts:
        lines.append("未发现疑似喊单。")
    for post, result in sorted(callouts, key=lambda item: item[0].created_at, reverse=True):
        lines.extend(
            [
                f"### {post.created_at.isoformat()} | {result.confidence:.2f}",
                "",
                f"- 链接: {post.url}",
                f"- 标的: {result.asset or '未知'}",
                f"- 方向: {result.side or '未知'}",
                f"- 原因: {result.reason}",
                "",
                "> " + post.text.replace("\n", "\n> "),
                "",
            ]
        )
    return "\n".join(lines)


def _counter_lines(counter: Counter) -> list[str]:
    if not counter:
        return ["暂无。"]
    return [f"- {key}: {value}" for key, value in counter.most_common(20)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze historical X posts for trading callouts.")
    parser.add_argument("--config", default="config.yaml", type=Path)
    parser.add_argument("--username", required=True)
    parser.add_argument("--output", default=".data/history-report.md", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--max-pages", default=10, type=int)
    parser.add_argument("--max-posts", type=int)
    args = parser.parse_args()

    analyze_history(
        config_path=args.config,
        username=args.username.lstrip("@"),
        output_path=args.output,
        max_pages=args.max_pages,
        max_posts=args.max_posts,
        json_output_path=args.json_output,
    )


if __name__ == "__main__":
    main()

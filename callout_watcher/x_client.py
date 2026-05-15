from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests


API_BASE = "https://api.x.com/2"


@dataclass(frozen=True)
class Post:
    id: str
    username: str
    text: str
    created_at: datetime
    url: str


class XClient:
    def __init__(self, bearer_token: str) -> None:
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {bearer_token}"})

    def get_user_id(self, username: str) -> str:
        response = self.session.get(
            f"{API_BASE}/users/by/username/{username}",
            params={"user.fields": "id,username"},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json().get("data")
        if not data or "id" not in data:
            raise ValueError(f"X user not found: @{username}")
        return str(data["id"])

    def get_latest_posts(
        self,
        username: str,
        user_id: str,
        since_id: str | None,
        include_replies: bool,
        include_retweets: bool,
        max_results: int = 10,
    ) -> list[Post]:
        exclude: list[str] = []
        if not include_replies:
            exclude.append("replies")
        if not include_retweets:
            exclude.append("retweets")

        params: dict[str, Any] = {
            "max_results": max(5, min(max_results, 100)),
            "tweet.fields": "created_at",
        }
        if since_id:
            params["since_id"] = since_id
        if exclude:
            params["exclude"] = ",".join(exclude)

        response = self.session.get(
            f"{API_BASE}/users/{user_id}/tweets",
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        posts = []
        for item in data:
            created_at = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
            post_id = str(item["id"])
            posts.append(
                Post(
                    id=post_id,
                    username=username,
                    text=item["text"],
                    created_at=created_at,
                    url=f"https://x.com/{username}/status/{post_id}",
                )
            )
        return sorted(posts, key=lambda post: int(post.id))

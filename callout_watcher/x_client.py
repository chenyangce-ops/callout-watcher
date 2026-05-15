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
        _raise_for_status(response)
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
        _raise_for_status(response)
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

    def get_posts_page(
        self,
        username: str,
        user_id: str,
        include_replies: bool,
        include_retweets: bool,
        pagination_token: str | None = None,
        max_results: int = 100,
    ) -> tuple[list[Post], str | None]:
        exclude: list[str] = []
        if not include_replies:
            exclude.append("replies")
        if not include_retweets:
            exclude.append("retweets")

        params: dict[str, Any] = {
            "max_results": max(5, min(max_results, 100)),
            "tweet.fields": "created_at",
        }
        if pagination_token:
            params["pagination_token"] = pagination_token
        if exclude:
            params["exclude"] = ",".join(exclude)

        response = self.session.get(
            f"{API_BASE}/users/{user_id}/tweets",
            params=params,
            timeout=20,
        )
        _raise_for_status(response)
        payload = response.json()
        posts = [self._post_from_api_item(username, item) for item in payload.get("data", [])]
        next_token = payload.get("meta", {}).get("next_token")
        return sorted(posts, key=lambda post: int(post.id)), next_token

    def get_post_history(
        self,
        username: str,
        user_id: str,
        include_replies: bool,
        include_retweets: bool,
        max_pages: int = 10,
        max_posts: int | None = None,
    ) -> list[Post]:
        posts: list[Post] = []
        next_token: str | None = None
        for _ in range(max_pages):
            page, next_token = self.get_posts_page(
                username=username,
                user_id=user_id,
                include_replies=include_replies,
                include_retweets=include_retweets,
                pagination_token=next_token,
            )
            posts.extend(page)
            if max_posts and len(posts) >= max_posts:
                return posts[:max_posts]
            if not next_token:
                break
        return posts

    @staticmethod
    def _post_from_api_item(username: str, item: dict[str, Any]) -> Post:
        created_at = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
        post_id = str(item["id"])
        return Post(
            id=post_id,
            username=username,
            text=item["text"],
            created_at=created_at,
            url=f"https://x.com/{username}/status/{post_id}",
        )


def _raise_for_status(response: requests.Response) -> None:
    if response.status_code == 402:
        raise RuntimeError(
            "X API returned 402 Payment Required. Add API credits or enable billing in the X Developer Console."
        )
    if response.status_code == 401:
        raise RuntimeError("X API returned 401 Unauthorized. Check X_BEARER_TOKEN in .env.")
    if response.status_code == 429:
        raise RuntimeError("X API returned 429 Too Many Requests. Wait for the rate limit window to reset.")
    response.raise_for_status()

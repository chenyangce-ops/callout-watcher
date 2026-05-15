from __future__ import annotations

import json
from pathlib import Path


class StateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.data = self._load()

    def get_since_id(self, username: str) -> str | None:
        value = self.data.get(username, {}).get("since_id")
        return str(value) if value else None

    def set_since_id(self, username: str, post_id: str) -> None:
        current = self.get_since_id(username)
        if current and int(current) >= int(post_id):
            return
        self.data.setdefault(username, {})["since_id"] = post_id
        self._save()

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

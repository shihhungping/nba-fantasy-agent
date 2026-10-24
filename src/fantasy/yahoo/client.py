"""只讀的 Yahoo Fantasy API client: 節流、重試、401 refresh、原始 JSON cache。

刻意只提供 get();不要加任何會改動 Yahoo 的方法。
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from fantasy.yahoo.endpoints import BASE_URL

RETRY_STATUS = frozenset({429, 500, 502, 503, 504, 999})  # 999 = Yahoo 限流


class YahooAPIError(Exception):
    def __init__(self, status: int, path: str, detail: str = "") -> None:
        super().__init__(f"Yahoo API {status} on {path}: {detail}".strip())
        self.status = status
        self.path = path


class SessionProvider(Protocol):
    @property
    def session(self) -> Any: ...

    def token_is_valid(self) -> bool: ...

    def refresh(self) -> None: ...


def slugify(path: str) -> str:
    return re.sub(r"[^A-Za-z0-9.=-]+", "_", path).strip("_")[:180]


class YahooClient:
    def __init__(
        self,
        auth: SessionProvider,
        *,
        interval_sec: float = 1.0,
        max_retries: int = 4,
        cache_dir: Path | None = None,
        fixture_dir: Path | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._auth = auth
        self._interval = interval_sec
        self._max_retries = max_retries
        self._cache_dir = cache_dir
        self._fixture_dir = fixture_dir
        self._fixtures_saved: set[str] = set()
        self._sleep = sleep
        self._clock = clock
        self._last_request: float | None = None
        self.calls = 0

    def get(self, path: str, *, kind: str | None = None) -> dict[str, Any]:
        """GET BASE_URL + path,回傳 fantasy_content。kind 用來命名 fixture (每種只存第一份)。"""
        if not self._auth.token_is_valid():
            self._auth.refresh()
        refreshed = False
        attempt = 0
        while True:
            resp = self._request(path)
            status = resp.status_code
            if status == 401 and not refreshed:
                self._auth.refresh()
                refreshed = True
                continue
            if status in RETRY_STATUS and attempt < self._max_retries:
                attempt += 1
                self._sleep(2.0**attempt)
                continue
            if status // 100 != 2:
                raise YahooAPIError(status, path, _error_detail(resp))
            break

        payload = resp.json()
        self._save(path, kind, payload)
        if "fantasy_content" not in payload:
            raise YahooAPIError(status, path, "回應沒有 fantasy_content")
        return payload["fantasy_content"]

    def _request(self, path: str):
        if self._last_request is not None:
            wait = self._interval - (self._clock() - self._last_request)
            if wait > 0:
                self._sleep(wait)
        self._last_request = self._clock()
        self.calls += 1
        return self._auth.session.get(BASE_URL + path, params={"format": "json"})

    def _save(self, path: str, kind: str | None, payload: dict) -> None:
        text = json.dumps(payload, ensure_ascii=False, indent=1)
        if self._cache_dir is not None:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            (self._cache_dir / f"{slugify(path)}.json").write_text(text, encoding="utf-8")
        if self._fixture_dir is not None and kind and kind not in self._fixtures_saved:
            self._fixture_dir.mkdir(parents=True, exist_ok=True)
            (self._fixture_dir / f"{kind}.json").write_text(text, encoding="utf-8")
            self._fixtures_saved.add(kind)


def _error_detail(resp) -> str:
    try:
        err = resp.json().get("error", {})
        return err.get("description", "") if isinstance(err, dict) else str(err)
    except ValueError:
        return (resp.text or "")[:200]

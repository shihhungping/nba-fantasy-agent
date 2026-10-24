"""Yahoo OAuth: 首次互動授權、token 載入/儲存、refresh。

Token 來源順序: 環境變數 YAHOO_ACCESS_TOKEN_JSON (雲端) → .secrets/yahoo_token.json (本機)。
任何地方都不印出 token 內容。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv

from fantasy import paths
from fantasy.config import LeagueConfig

TOKEN_ENV_VAR = "YAHOO_ACCESS_TOKEN_JSON"
TOKEN_FIELDS = (
    "access_token",
    "consumer_key",
    "consumer_secret",
    "guid",
    "refresh_token",
    "token_time",
    "token_type",
)


class AuthError(Exception):
    """找不到 token、token 格式錯,或缺 consumer key/secret。"""


def token_path() -> Path:
    return paths.repo_root() / ".secrets" / "yahoo_token.json"


@dataclass
class TokenSource:
    kind: Literal["env", "file"]
    data: dict[str, Any]


def load_token() -> TokenSource:
    raw = os.environ.get(TOKEN_ENV_VAR)
    if raw:
        return TokenSource("env", _validate(json.loads(raw), TOKEN_ENV_VAR))
    path = token_path()
    if path.is_file():
        return TokenSource("file", _validate(json.loads(path.read_text(encoding="utf-8")), str(path)))
    raise AuthError(f"找不到 Yahoo token: 請先在本機執行 `fantasy auth`,或設定環境變數 {TOKEN_ENV_VAR}")


def save_token(data: dict[str, Any]) -> Path:
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: data.get(k) for k in TOKEN_FIELDS}, indent=2), encoding="utf-8")
    return path


def _validate(data: Any, where: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise AuthError(f"{where} 不是 JSON object")
    missing = [
        k
        for k in ("access_token", "refresh_token", "token_type", "consumer_key", "consumer_secret")
        if not data.get(k)
    ]
    if missing:
        raise AuthError(f"{where} 缺少欄位: {missing}")
    return data


def _consumer_credentials() -> tuple[str, str]:
    load_dotenv(paths.repo_root() / ".env", override=False)
    key, secret = os.environ.get("YAHOO_CONSUMER_KEY"), os.environ.get("YAHOO_CONSUMER_SECRET")
    if not key or not secret:
        raise AuthError("缺少 YAHOO_CONSUMER_KEY / YAHOO_CONSUMER_SECRET (.env 或環境變數)")
    return key, secret


def run_auth_flow(league: LeagueConfig) -> Path:
    """互動授權: 開瀏覽器 → 使用者把 Yahoo 顯示的 verifier 貼回終端 → 存 token。"""
    from yfpy.query import YahooFantasySportsQuery

    key, secret = _consumer_credentials()
    q = YahooFantasySportsQuery(
        league_id=str(league.league.league_id),
        game_code=league.league.game_code,
        yahoo_consumer_key=key,
        yahoo_consumer_secret=secret,
        env_var_fallback=False,
        browser_callback=True,
    )
    return save_token(q._yahoo_access_token_dict)


class OAuthSession:
    """包住 yahoo_oauth 的 OAuth2: 提供 session 與 refresh。refresh 後回寫 token (file 來源才寫檔)。"""

    def __init__(self, source: TokenSource | None = None) -> None:
        from yahoo_oauth import OAuth2

        self.source = source or load_token()
        d = self.source.data
        self._oauth = OAuth2(
            d["consumer_key"],
            d["consumer_secret"],
            access_token=d["access_token"],
            guid=d.get("guid"),
            refresh_token=d["refresh_token"],
            token_time=float(d.get("token_time") or 0.0),
            token_type=d["token_type"],
            browser_callback=False,
            store_file=False,
        )
        self.refresh_token_rotated: bool | None = None
        self._sync_token()

    @property
    def session(self):
        return self._oauth.session

    def token_is_valid(self) -> bool:
        return self._oauth.token_is_valid()

    def refresh(self) -> None:
        old_refresh = self._oauth.refresh_token
        self._oauth.refresh_access_token()
        self._oauth.session = self._oauth.oauth.get_session(token=self._oauth.access_token)
        self.refresh_token_rotated = self._oauth.refresh_token != old_refresh
        self._sync_token()

    def _sync_token(self) -> None:
        o = self._oauth
        updated = {
            **self.source.data,
            "access_token": o.access_token,
            "refresh_token": o.refresh_token,
            "token_time": o.token_time,
            "token_type": o.token_type,
        }
        if updated != self.source.data:
            self.source.data = updated
            if self.source.kind == "file":
                save_token(updated)

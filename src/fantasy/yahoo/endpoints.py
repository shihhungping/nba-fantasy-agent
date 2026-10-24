"""Yahoo Fantasy API v2 的 resource path (純函式)。回應一律用 format=json。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2/"


def league_key(game_key: str, league_id: int) -> str:
    return f"{game_key}.l.{league_id}"


def game_by_season(game_code: str, season: int) -> str:
    return f"games;game_codes={game_code};seasons={season}"


def game_stat_categories(game_key: str) -> str:
    return f"game/{game_key}/stat_categories"


def league_settings(lk: str) -> str:
    return f"league/{lk}/settings"


def league_teams(lk: str) -> str:
    return f"league/{lk}/teams"


def team_roster(team_key: str, day: date) -> str:
    return f"team/{team_key}/roster;date={day.isoformat()}"


def players_stats_by_date(lk: str, player_keys: Sequence[str], day: date) -> str:
    if not 1 <= len(player_keys) <= 25:
        raise ValueError(f"player_keys 一次 1-25 個,實際 {len(player_keys)}")
    return f"league/{lk}/players;player_keys={','.join(player_keys)}/stats;type=date;date={day.isoformat()}"


def league_players(lk: str, *, sort: str, start: int, count: int, status: str | None = None) -> str:
    """status: None = 全部、A = 可簽 (FA+W)、FA、W、T = 已被選。sort: AR = 本季排名、OR = 季前排名。"""
    if not 1 <= count <= 25:
        raise ValueError("count 一次 1-25")
    status_part = f";status={status}" if status else ""
    return f"league/{lk}/players{status_part};sort={sort};start={start};count={count}"


def scoreboard(lk: str, week: int) -> str:
    return f"league/{lk}/scoreboard;week={week}"


def transactions(lk: str) -> str:
    return f"league/{lk}/transactions"

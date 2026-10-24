"""Phase 1 一次性: 每種 Yahoo endpoint 抓一份原始回應存到 tests/fixtures/yahoo/,用來寫 parser。

只讀。用法: .venv/Scripts/python scripts/capture_fixtures.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fantasy.config import load_league_config
from fantasy.yahoo import endpoints as ep
from fantasy.yahoo.auth import OAuthSession
from fantasy.yahoo.client import YahooClient

ROOT = Path(__file__).resolve().parents[1]


def find_all(node, key):
    """遞迴找出所有 key 對應的值 (只用來在擷取時挑 team_key / player_key)。"""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                yield v
            yield from find_all(v, key)
    elif isinstance(node, list):
        for v in node:
            yield from find_all(v, key)


def main() -> None:
    league = load_league_config()
    client = YahooClient(
        OAuthSession(),
        cache_dir=ROOT / ".cache" / "yahoo" / "capture",
        fixture_dir=ROOT / "tests" / "fixtures" / "yahoo",
    )
    season = int(league.league.season[:4])
    game = client.get(ep.game_by_season(league.league.game_code, season), kind="game")
    game_key = next(find_all(game, "game_key"))
    lk = ep.league_key(game_key, league.league.league_id)
    print("game_key", game_key, "league_key", lk)

    client.get(ep.game_stat_categories(game_key), kind="game_stat_categories")
    client.get(ep.league_settings(lk), kind="league_settings")
    teams = client.get(ep.league_teams(lk), kind="league_teams")
    team_keys = sorted(set(find_all(teams, "team_key")))
    print("teams", len(team_keys))

    my_key = None
    for tk, name in zip(find_all(teams, "team_key"), find_all(teams, "name"), strict=False):
        if name == league.league.my_team_name:
            my_key = tk
    print("my team found:", my_key is not None)
    my_key = my_key or team_keys[0]

    roster = client.get(ep.team_roster(my_key, date(2026, 10, 23)), kind="team_roster")
    player_keys = list(dict.fromkeys(find_all(roster, "player_key")))
    print("roster players", len(player_keys))
    client.get(ep.players_stats_by_date(lk, player_keys, date(2026, 10, 23)), kind="players_stats_date")
    client.get(ep.league_players(lk, status="A", sort="AR", start=0, count=25), kind="players_available_ar")
    client.get(ep.league_players(lk, sort="OR", start=0, count=25), kind="players_all_or")
    client.get(ep.scoreboard(lk, 1), kind="scoreboard")
    client.get(ep.transactions(lk), kind="transactions")
    print("calls", client.calls)


if __name__ == "__main__":
    main()

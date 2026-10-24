import json
from datetime import date

import pytest

from fantasy.yahoo import endpoints
from fantasy.yahoo.client import YahooAPIError, YahooClient


class FakeResponse:
    def __init__(self, status: int, payload: dict | None = None) -> None:
        self.status_code = status
        self._payload = payload if payload is not None else {}
        self.text = json.dumps(self._payload)

    def json(self) -> dict:
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.urls: list[str] = []

    def get(self, url, params=None):
        assert params == {"format": "json"}
        self.urls.append(url)
        return self.responses.pop(0)


class FakeAuth:
    def __init__(self, responses, valid: bool = True) -> None:
        self.session = FakeSession(responses)
        self.valid = valid
        self.refreshes = 0

    def token_is_valid(self) -> bool:
        return self.valid

    def refresh(self) -> None:
        self.refreshes += 1
        self.valid = True


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.now += s


OK = {"fantasy_content": {"x": 1}}


def make_client(responses, valid=True, **kw):
    auth = FakeAuth(responses, valid)
    clk = FakeClock()
    client = YahooClient(auth, sleep=clk.sleep, clock=clk.clock, **kw)
    return client, auth, clk


def test_get_returns_fantasy_content():
    client, auth, _ = make_client([FakeResponse(200, OK)])
    assert client.get("league/x/settings") == {"x": 1}
    assert auth.session.urls == [endpoints.BASE_URL + "league/x/settings"]
    assert client.calls == 1


def test_throttle_between_requests():
    client, _, clk = make_client([FakeResponse(200, OK)] * 3, interval_sec=1.0)
    for _ in range(3):
        client.get("a")
    assert clk.sleeps == [1.0, 1.0]


@pytest.mark.parametrize("status", [999, 429, 503])
def test_retry_then_success(status):
    client, _, clk = make_client([FakeResponse(status), FakeResponse(status), FakeResponse(200, OK)])
    assert client.get("a") == {"x": 1}
    assert client.calls == 3
    assert 2.0 in clk.sleeps and 4.0 in clk.sleeps


def test_retry_exhausted_raises():
    client, _, _ = make_client([FakeResponse(999)] * 3, max_retries=2)
    with pytest.raises(YahooAPIError) as e:
        client.get("a")
    assert e.value.status == 999


def test_401_refreshes_once():
    client, auth, _ = make_client([FakeResponse(401), FakeResponse(200, OK)])
    assert client.get("a") == {"x": 1}
    assert auth.refreshes == 1


def test_repeated_401_raises():
    client, _, _ = make_client([FakeResponse(401), FakeResponse(401)])
    with pytest.raises(YahooAPIError):
        client.get("a")


def test_expired_token_refreshed_before_request():
    client, auth, _ = make_client([FakeResponse(200, OK)], valid=False)
    client.get("a")
    assert auth.refreshes == 1


def test_not_found_error_detail():
    client, _, _ = make_client([FakeResponse(400, {"error": {"description": "bad league"}})])
    with pytest.raises(YahooAPIError, match="bad league"):
        client.get("a")


def test_cache_and_fixture_written(tmp_path):
    cache, fx = tmp_path / "cache", tmp_path / "fx"
    client, _, _ = make_client(
        [FakeResponse(200, OK), FakeResponse(200, {"fantasy_content": {"x": 2}})],
        cache_dir=cache,
        fixture_dir=fx,
    )
    client.get("team/1/roster;date=2026-10-20", kind="roster")
    client.get("team/2/roster;date=2026-10-20", kind="roster")
    assert len(list(cache.glob("*.json"))) == 2
    saved = json.loads((fx / "roster.json").read_text(encoding="utf-8"))
    assert saved["fantasy_content"] == {"x": 1}  # 每種 kind 只存第一份


def test_client_is_read_only():
    public = {n for n in dir(YahooClient) if not n.startswith("_")}
    assert public == {"get"}


def test_endpoints():
    lk = endpoints.league_key("466", 23840)
    assert lk == "466.l.23840"
    assert endpoints.team_roster("466.l.23840.t.3", date(2026, 10, 23)).endswith("roster;date=2026-10-23")
    path = endpoints.players_stats_by_date(lk, ["466.p.1", "466.p.2"], date(2026, 10, 23))
    assert "player_keys=466.p.1,466.p.2/stats;type=date;date=2026-10-23" in path
    with pytest.raises(ValueError):
        endpoints.players_stats_by_date(lk, [f"p{i}" for i in range(26)], date(2026, 10, 23))

import pytest

from fantasy.budget import compute_budget


def test_week1_fresh(league, model):
    b = compute_budget(1, 0, 0, league, model)
    assert b.weekly_cap == 3  # floor(75 / 19)
    assert b.this_week_remaining == 3
    assert b.season_remaining == 90


def test_mid_week_usage_does_not_move_cap(league, model):
    b = compute_budget(1, 0, 2, league, model)
    assert b.weekly_cap == 3
    assert b.this_week_remaining == 1
    assert b.season_remaining == 88


def test_over_cap_this_week_clamps_to_zero(league, model):
    b = compute_budget(1, 0, 5, league, model)
    assert b.this_week_remaining == 0


def test_capped_by_weekly_max(league, model):
    # week 19 單週剩餘: floor((75 − 60) / 1) = 15 → min(5, 15) = 5
    assert compute_budget(19, 60, 0, league, model).weekly_cap == 5


def test_late_season_floor(league, model):
    # week 15, 已用 66: floor(9 / 5) = 1
    assert compute_budget(15, 66, 0, league, model).weekly_cap == 1


def test_regular_season_pool_exhausted(league, model):
    b = compute_budget(10, 80, 0, league, model)
    assert b.weekly_cap == 0
    assert b.season_remaining == 10


def test_playoff_week(league, model):
    b = compute_budget(20, 75, 1, league, model)
    assert b.weekly_cap == 5
    assert b.this_week_remaining == 4
    assert b.season_remaining == 14


def test_playoff_week_limited_by_season_max(league, model):
    assert compute_budget(22, 87, 0, league, model).weekly_cap == 3


@pytest.mark.parametrize(
    ("week", "before", "this"),
    [(0, 0, 0), (23, 0, 0), (1, -1, 0), (1, 0, -1), (5, 89, 2)],
)
def test_invalid_inputs(league, model, week, before, this):
    with pytest.raises(ValueError):
        compute_budget(week, before, this, league, model)

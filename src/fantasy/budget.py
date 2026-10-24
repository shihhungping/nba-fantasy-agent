"""異動預算 (methodology §7)。

週初基準: used_before_week = 本週以前累計已用次數;剩餘例行賽週數含本週。
例行賽每週上限 = min(weekly_max, floor((season_max − reserve − used_before_week) / 剩餘例行賽週數))。
季後賽週上限 = min(weekly_max, season_max − used_before_week)。
"""

from __future__ import annotations

from dataclasses import dataclass

from fantasy.config import LeagueConfig, ModelConfig


@dataclass(frozen=True)
class TransactionBudget:
    week: int
    weekly_cap: int  # 本週建議上限 (週初決定,週中不變)
    this_week_remaining: int  # 本週上限 − 本週已用
    season_remaining: int  # 整季硬上限剩餘次數 (含季後賽保留)


def compute_budget(
    week: int,
    used_before_week: int,
    used_this_week: int,
    league: LeagueConfig,
    model: ModelConfig,
) -> TransactionBudget:
    tx, sched = league.transactions, league.schedule
    if not 1 <= week <= sched.last_week:
        raise ValueError(f"week 必須介於 1 與 {sched.last_week} 之間,實際 {week}")
    if used_before_week < 0 or used_this_week < 0:
        raise ValueError("已用次數不能為負")
    if used_before_week + used_this_week > tx.season_max:
        raise ValueError(f"已用次數合計 {used_before_week + used_this_week} 超過 season_max {tx.season_max}")

    if week <= sched.regular_season_weeks:
        pool = max(0, tx.season_max - model.transaction_budget.reserve_for_playoffs - used_before_week)
        weeks_left = sched.regular_season_weeks - week + 1
        weekly_cap = min(tx.weekly_max, pool // weeks_left)
    else:
        weekly_cap = min(tx.weekly_max, tx.season_max - used_before_week)

    return TransactionBudget(
        week=week,
        weekly_cap=weekly_cap,
        this_week_remaining=max(0, weekly_cap - used_this_week),
        season_remaining=tx.season_max - used_before_week - used_this_week,
    )

"""config/league.yaml 與 config/model.yaml 的 pydantic 模型與載入。

驗證失敗一律 raise ConfigError,不做 fallback。
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from fantasy import paths

PLAYER_POSITIONS = frozenset({"PG", "SG", "SF", "PF", "C"})
PRIOR_SRCS = frozenset({"P", "S", "E"})


class ConfigError(Exception):
    """設定檔不存在、YAML 格式錯或驗證失敗。"""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------- league.yaml ----------


class LeagueInfo(_Strict):
    name: str
    league_id: int
    game_code: str
    season: str
    num_teams: int
    scoring_type: Literal["head_to_head_categories"]
    my_team_name: str
    my_team_alias_in_draft: str


class Category(_Strict):
    key: str
    label: str
    yahoo_name: str
    kind: Literal["counting", "percentage"]
    higher_is_better: bool
    components: tuple[str, str] | None = None

    @model_validator(mode="after")
    def _components_match_kind(self) -> Category:
        if self.kind == "percentage" and self.components is None:
            raise ValueError(f"percentage 類別 {self.key} 必須有 components [makes, attempts]")
        if self.kind == "counting" and self.components is not None:
            raise ValueError(f"counting 類別 {self.key} 不應有 components")
        return self


class Matchup(_Strict):
    categories_total: int
    win_threshold_note: str


class Roster(_Strict):
    slots: dict[str, int]
    active_slots: list[str]
    eligibility: dict[str, list[str]]
    lineup_lock: Literal["daily", "weekly"]

    @model_validator(mode="after")
    def _slots_consistent(self) -> Roster:
        unknown_active = set(self.active_slots) - set(self.slots)
        if unknown_active:
            raise ValueError(f"active_slots 不在 slots 中: {sorted(unknown_active)}")
        if set(self.eligibility) != set(self.slots):
            raise ValueError(
                f"eligibility 的 slot 與 slots 不一致: {sorted(set(self.eligibility) ^ set(self.slots))}"
            )
        for slot, positions in self.eligibility.items():
            bad = set(positions) - PLAYER_POSITIONS
            if bad:
                raise ValueError(f"eligibility[{slot}] 有未知位置: {sorted(bad)}")
        if any(n < 0 for n in self.slots.values()):
            raise ValueError("slots 格數不能為負")
        return self

    @property
    def active_slot_count(self) -> int:
        return sum(self.slots[s] for s in self.active_slots)


class Transactions(_Strict):
    weekly_max: int
    season_max: int
    waiver_type: str
    waiver_days: int
    injured_to_il_direct: bool


class Schedule(_Strict):
    regular_season_weeks: int
    playoff_teams: int
    playoff_weeks: list[int]
    season_end_date: date
    week_start_day: Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    @model_validator(mode="after")
    def _playoff_weeks_follow_regular_season(self) -> Schedule:
        first = self.regular_season_weeks + 1
        expected = list(range(first, first + len(self.playoff_weeks)))
        if not self.playoff_weeks or self.playoff_weeks != expected:
            raise ValueError(f"playoff_weeks 應緊接例行賽週次 {expected},實際 {self.playoff_weeks}")
        return self

    @property
    def last_week(self) -> int:
        return self.playoff_weeks[-1]


class Report(_Strict):
    display_timezone: str


class LeagueConfig(_Strict):
    league: LeagueInfo
    categories: list[Category]
    prior_columns: dict[str, str]
    matchup: Matchup
    roster: Roster
    transactions: Transactions
    schedule: Schedule
    report: Report
    team_aliases: dict[str, str]

    @model_validator(mode="after")
    def _cross_checks(self) -> LeagueConfig:
        keys = [c.key for c in self.categories]
        if len(keys) != len(set(keys)):
            raise ValueError(f"categories key 重複: {keys}")
        if set(self.prior_columns) != set(keys):
            raise ValueError(
                f"prior_columns 與 categories key 不一致: {sorted(set(self.prior_columns) ^ set(keys))}"
            )
        if self.matchup.categories_total != len(keys):
            raise ValueError(
                f"matchup.categories_total={self.matchup.categories_total} 與類別數 {len(keys)} 不符"
            )
        if self.transactions.weekly_max > self.transactions.season_max:
            raise ValueError("transactions.weekly_max 不能大於 season_max")
        not_upper = [t for t in [*self.team_aliases, *self.team_aliases.values()] if t != t.upper()]
        if not_upper:
            raise ValueError(f"team_aliases 必須全大寫: {not_upper}")
        chained = set(self.team_aliases) & set(self.team_aliases.values())
        if chained:
            raise ValueError(f"team_aliases 的標準碼不能同時是別名: {sorted(chained)}")
        return self

    @property
    def category_keys(self) -> list[str]:
        return [c.key for c in self.categories]

    def categories_by_kind(self, kind: Literal["counting", "percentage"]) -> list[Category]:
        return [c for c in self.categories if c.kind == kind]

    def canonical_team(self, team: str) -> str:
        """把各來源的球隊縮寫正規化成 NBA 官方 3 碼。"""
        t = team.strip().upper()
        return self.team_aliases.get(t, t)


# ---------- model.yaml ----------


class Pool(_Strict):
    size: int
    min_gp_for_pool: int
    iterations: int


class SampleThresholds(_Strict):
    role_only_max_gp: int
    counting_min_gp: int
    pct_min_gp: int

    @model_validator(mode="after")
    def _ordered(self) -> SampleThresholds:
        if not self.role_only_max_gp < self.counting_min_gp <= self.pct_min_gp:
            raise ValueError("sample_thresholds 需滿足 role_only_max_gp < counting_min_gp <= pct_min_gp")
        return self


class BlendK(_Strict):
    counting: float
    fg_pct: float
    ft_pct: float


class Blend(_Strict):
    k: BlendK
    src_k_multiplier: dict[Literal["P", "S", "E"], float]
    no_prior_policy: Literal["actual_only"]

    @model_validator(mode="after")
    def _all_srcs(self) -> Blend:
        missing = PRIOR_SRCS - set(self.src_k_multiplier)
        if missing:
            raise ValueError(f"src_k_multiplier 缺少: {sorted(missing)}")
        return self


class RoleSignals(_Strict):
    mpg_change_flag: float
    recent_window_games: int
    fga_change_flag_pct: float


class Flags(_Strict):
    delta_z_flag: float


class TransactionBudgetConfig(_Strict):
    reserve_for_playoffs: int


class Punt(_Strict):
    allowed: list[str]
    never: list[str]
    max_punt: int
    trigger_threshold: float
    min_weeks_before_change: int

    @model_validator(mode="after")
    def _disjoint(self) -> Punt:
        overlap = set(self.allowed) & set(self.never)
        if overlap:
            raise ValueError(f"punt.allowed 與 punt.never 重疊: {sorted(overlap)}")
        return self


class Prediction(_Strict):
    method: Literal["monte_carlo"]
    n_sims: int
    seed: int
    min_games_for_resample: int


class Backtest(_Strict):
    calibration_bins: list[float]
    recommendation_eval_weeks: list[int]

    @model_validator(mode="after")
    def _bins_sorted(self) -> Backtest:
        b = self.calibration_bins
        if len(b) < 2 or b != sorted(b) or b[0] != 0.0 or b[-1] != 1.0:
            raise ValueError("calibration_bins 必須遞增且從 0.0 到 1.0")
        return self


class ModelConfig(_Strict):
    pool: Pool
    sample_thresholds: SampleThresholds
    blend: Blend
    role_signals: RoleSignals
    flags: Flags
    transaction_budget: TransactionBudgetConfig
    punt: Punt
    prediction: Prediction
    backtest: Backtest


# ---------- loading ----------


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        raise ConfigError(f"設定檔不存在: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML 格式錯誤: {path}\n{e}") from e
    if not isinstance(data, dict):
        raise ConfigError(f"設定檔最上層必須是 mapping: {path}")
    return data


def load_league_config(path: Path | str | None = None) -> LeagueConfig:
    path = Path(path) if path else paths.league_config_path()
    try:
        return LeagueConfig.model_validate(_read_yaml(path))
    except ValidationError as e:
        raise ConfigError(f"league config 驗證失敗: {path}\n{e}") from e


def load_model_config(path: Path | str | None = None) -> ModelConfig:
    path = Path(path) if path else paths.model_config_path()
    try:
        return ModelConfig.model_validate(_read_yaml(path))
    except ValidationError as e:
        raise ConfigError(f"model config 驗證失敗: {path}\n{e}") from e


def validate_consistency(league: LeagueConfig, model: ModelConfig) -> None:
    """跨檔檢查 league.yaml 與 model.yaml。"""
    keys = set(league.category_keys)
    unknown = (set(model.punt.allowed) | set(model.punt.never)) - keys
    if unknown:
        raise ConfigError(f"punt 設定有不存在的類別: {sorted(unknown)}")
    uncovered = keys - set(model.punt.allowed) - set(model.punt.never)
    if uncovered:
        raise ConfigError(f"類別未出現在 punt.allowed 或 punt.never: {sorted(uncovered)}")
    pct_keys = {c.key for c in league.categories_by_kind("percentage")}
    blend_pct_keys = set(BlendK.model_fields) - {"counting"}
    if pct_keys != blend_pct_keys:
        raise ConfigError(
            f"blend.k 的百分比類別 {sorted(blend_pct_keys)} 與 league 的 {sorted(pct_keys)} 不一致"
        )
    if model.transaction_budget.reserve_for_playoffs > league.transactions.season_max:
        raise ConfigError("reserve_for_playoffs 不能大於 season_max")


def load_configs() -> tuple[LeagueConfig, ModelConfig]:
    league, model = load_league_config(), load_model_config()
    validate_consistency(league, model)
    return league, model

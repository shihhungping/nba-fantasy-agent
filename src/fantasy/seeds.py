"""Seed data loader: prior z-score、選秀結果、手動陣容快照。

每個 loader 驗證欄位與型別,失敗 raise SeedDataError。球隊縮寫一律轉成 NBA 官方 3 碼
(league.yaml team_aliases),positions 轉成 list。
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd

from fantasy import paths
from fantasy.config import PLAYER_POSITIONS, PRIOR_SRCS, LeagueConfig, load_league_config
from fantasy.names import name_key, short_key

PRIOR_BASE_COLUMNS = [
    "prior_rank", "player_name", "nba_team", "positions",
    "draft_bid_value", "market_value", "src", "note",
]  # fmt: skip
DRAFT_COLUMNS = ["round", "pick", "player_short", "positions", "nba_team", "manager", "price"]
ROSTER_STAT_COLUMNS = [
    "gp", "fgm", "fga", "ftm", "fta", "fg3m", "pts", "reb", "ast", "stl", "blk", "tov", "dd",
]  # fmt: skip
ROSTER_COLUMNS = [
    "snapshot_date", "slot", "player_name", "nba_team", "positions", "status",
    "yahoo_rank_preseason", "yahoo_rank_current", "mpg", *ROSTER_STAT_COLUMNS, "note",
]  # fmt: skip


class SeedDataError(Exception):
    """Seed CSV 欄位缺漏、型別錯誤或內容違反約束。"""


def _read_csv(path: Path, required: list[str]) -> pd.DataFrame:
    if not path.is_file():
        raise SeedDataError(f"檔案不存在: {path}")
    try:
        # index_col=False: 欄數比 header 多時不要把第一欄默默當成 index;ParserWarning 升級成錯誤
        with warnings.catch_warnings():
            warnings.simplefilter("error", pd.errors.ParserWarning)
            df = pd.read_csv(path, encoding="utf-8", dtype=str, keep_default_na=False, index_col=False)
    except (pd.errors.ParserError, pd.errors.ParserWarning) as e:
        raise SeedDataError(f"{path.name} CSV 格式錯誤 (含逗號的欄位要加引號): {e}") from e
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SeedDataError(f"{path.name} 缺少欄位: {missing}")
    return df


def _to_numeric(df: pd.DataFrame, cols: list[str], path: Path, integer: bool = False) -> None:
    for col in cols:
        values = pd.to_numeric(df[col], errors="coerce")
        if values.isna().any():
            bad = df.loc[values.isna(), col].tolist()
            raise SeedDataError(f"{path.name} 欄位 {col} 有非數值或空值: {bad}")
        if integer:
            if (values % 1 != 0).any():
                raise SeedDataError(f"{path.name} 欄位 {col} 必須是整數")
            values = values.astype("int64")
        df[col] = values


def _parse_positions(df: pd.DataFrame, path: Path) -> None:
    positions = df["positions"].map(lambda s: [p.strip() for p in s.split("/") if p.strip()])
    bad = positions[positions.map(lambda ps: not ps or not set(ps) <= PLAYER_POSITIONS)]
    if not bad.empty:
        raise SeedDataError(f"{path.name} 有無效 positions: {df.loc[bad.index, 'positions'].tolist()}")
    df["positions"] = positions


def _canonical_teams(df: pd.DataFrame, league: LeagueConfig) -> None:
    df["nba_team"] = df["nba_team"].map(league.canonical_team)


def load_prior(path: Path | str | None = None, league: LeagueConfig | None = None) -> pd.DataFrame:
    """data/prior/prior_z_2026-27.csv。z 欄名從 league.prior_columns 取。加上 name_key 欄。"""
    path = Path(path) if path else paths.prior_path()
    league = league or load_league_config()
    z_cols = list(league.prior_columns.values())
    df = _read_csv(path, PRIOR_BASE_COLUMNS + z_cols)

    _to_numeric(df, ["prior_rank", "draft_bid_value", "market_value"], path, integer=True)
    _to_numeric(df, z_cols, path)
    bad_src = sorted(set(df["src"]) - PRIOR_SRCS)
    if bad_src:
        raise SeedDataError(f"{path.name} src 只能是 {sorted(PRIOR_SRCS)},實際有: {bad_src}")
    dup = df.loc[df["player_name"].duplicated(), "player_name"].tolist()
    if dup:
        raise SeedDataError(f"{path.name} player_name 重複: {dup}")
    _parse_positions(df, path)
    _canonical_teams(df, league)

    df["name_key"] = df["player_name"].map(name_key)
    dup_key = df.loc[df["name_key"].duplicated(), "player_name"].tolist()
    if dup_key:
        raise SeedDataError(f"{path.name} 正規化後名字重複: {dup_key}")
    return df


def load_draft(path: Path | str | None = None, league: LeagueConfig | None = None) -> pd.DataFrame:
    """data/draft/draft_results_2026-27.csv。加上 short_key 欄。"""
    path = Path(path) if path else paths.draft_path()
    league = league or load_league_config()
    df = _read_csv(path, DRAFT_COLUMNS)

    _to_numeric(df, ["round", "pick", "price"], path, integer=True)
    if df["pick"].duplicated().any():
        raise SeedDataError(f"{path.name} pick 重複: {df.loc[df['pick'].duplicated(), 'pick'].tolist()}")
    _parse_positions(df, path)
    _canonical_teams(df, league)
    df["short_key"] = df["player_short"].map(short_key)
    return df


def load_manual_roster(path: Path | str | None = None, league: LeagueConfig | None = None) -> pd.DataFrame:
    """data/manual/my_roster_*.csv。數據是季累計,mpg 是平均。"""
    path = Path(path) if path else paths.manual_roster_path()
    league = league or load_league_config()
    df = _read_csv(path, ROSTER_COLUMNS)

    try:
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], format="%Y-%m-%d").dt.date
    except ValueError as e:
        raise SeedDataError(f"{path.name} snapshot_date 格式需為 YYYY-MM-DD: {e}") from e
    _to_numeric(df, ["yahoo_rank_preseason", "yahoo_rank_current", *ROSTER_STAT_COLUMNS], path, integer=True)
    _to_numeric(df, ["mpg"], path)
    bad_slot = sorted(set(df["slot"]) - set(league.roster.slots))
    if bad_slot:
        raise SeedDataError(f"{path.name} 有未知 slot: {bad_slot}")
    _parse_positions(df, path)
    _canonical_teams(df, league)
    df["name_key"] = df["player_name"].map(name_key)
    return df

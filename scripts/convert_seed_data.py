"""把季前 seed data 轉成乾淨的 CSV。只需要跑一次,輸出已 commit 在 data/。

- data/prior/source/price_sheet_2026-27.md  -> data/prior/prior_z_2026-27.csv
- data/draft/source/draft_results_raw.csv   -> data/draft/draft_results_2026-27.csv

draft_results_raw.csv 的 Position 欄位沒有加引號 (例如 "PG,SG,SF" 被拆成多欄),
所以用「前 3 欄 + 後 3 欄固定,中間都是位置」的方式解析。
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PRIOR_SRC = ROOT / "data/prior/source/price_sheet_2026-27.md"
PRIOR_OUT = ROOT / "data/prior/prior_z_2026-27.csv"
DRAFT_SRC = ROOT / "data/draft/source/draft_results_raw.csv"
DRAFT_OUT = ROOT / "data/draft/draft_results_2026-27.csv"

CATS = ["FG%", "FT%", "3PM", "PTS", "REB", "AST", "STL", "BLK", "TO", "DD"]
CAT_COLS = ["z_fg_pct", "z_ft_pct", "z_3pm", "z_pts", "z_reb", "z_ast", "z_stl", "z_blk", "z_to", "z_dd"]


def money(s: str) -> int:
    return int(s.strip().lstrip("$"))


def convert_prior() -> int:
    rows = []
    for line in PRIOR_SRC.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\| \d+ \|", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rank, name, team, pos, bid, mkt, *rest = cells
        zs, src, note = rest[:10], rest[10], rest[11] if len(rest) > 11 else ""
        rows.append(
            {
                "prior_rank": int(rank),
                "player_name": name,
                "nba_team": team,
                "positions": pos,
                "draft_bid_value": money(bid),
                "market_value": money(mkt),
                **{col: float(z) for col, z in zip(CAT_COLS, zs)},
                "src": src,
                "note": note,
            }
        )
    with PRIOR_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def convert_draft() -> int:
    rows = []
    with DRAFT_SRC.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for parts in reader:
            if not parts:
                continue
            rnd, pick, player = parts[0], parts[1], parts[2]
            team, manager, price = parts[-3], parts[-2], parts[-1]
            positions = "/".join(parts[3:-3])
            rows.append(
                {
                    "round": int(rnd),
                    "pick": int(pick),
                    "player_short": player,
                    "positions": positions,
                    "nba_team": team,
                    "manager": manager,
                    "price": money(price),
                }
            )
    rows.sort(key=lambda r: r["pick"])
    with DRAFT_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    n_prior = convert_prior()
    n_draft = convert_draft()
    print(f"prior rows: {n_prior}, draft rows: {n_draft}")

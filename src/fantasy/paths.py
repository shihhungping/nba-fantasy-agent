"""Repo 內的標準路徑。設環境變數 FANTASY_ROOT 可覆寫 repo 根目錄。"""

import os
from pathlib import Path


def repo_root() -> Path:
    env = os.environ.get("FANTASY_ROOT")
    if env:
        return Path(env).resolve()
    # src/fantasy/paths.py -> repo root (editable install)
    return Path(__file__).resolve().parents[2]


def league_config_path() -> Path:
    return repo_root() / "config" / "league.yaml"


def model_config_path() -> Path:
    return repo_root() / "config" / "model.yaml"


def prior_path() -> Path:
    return repo_root() / "data" / "prior" / "prior_z_2026-27.csv"


def draft_path() -> Path:
    return repo_root() / "data" / "draft" / "draft_results_2026-27.csv"


def manual_roster_path() -> Path:
    return repo_root() / "data" / "manual" / "my_roster_2026-10-24.csv"

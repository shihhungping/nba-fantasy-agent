from pathlib import Path

import pytest
import yaml

from fantasy import paths
from fantasy.config import LeagueConfig, ModelConfig, load_league_config, load_model_config


@pytest.fixture(scope="session")
def league() -> LeagueConfig:
    return load_league_config()


@pytest.fixture(scope="session")
def model() -> ModelConfig:
    return load_model_config()


@pytest.fixture
def raw_league() -> dict:
    return yaml.safe_load(paths.league_config_path().read_text(encoding="utf-8"))


@pytest.fixture
def raw_model() -> dict:
    return yaml.safe_load(paths.model_config_path().read_text(encoding="utf-8"))


@pytest.fixture
def write_yaml(tmp_path: Path):
    def _write(data: dict, name: str = "cfg.yaml") -> Path:
        p = tmp_path / name
        p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        return p

    return _write

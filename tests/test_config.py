import pytest

from fantasy.config import (
    ConfigError,
    load_configs,
    load_league_config,
    load_model_config,
    validate_consistency,
)


def test_real_configs_load(league, model):
    assert league.league.league_id == 23840
    assert league.league.num_teams == 12
    assert len(league.categories) == 10
    assert {c.key for c in league.categories_by_kind("percentage")} == {"fg_pct", "ft_pct"}
    assert league.roster.active_slot_count == 10
    assert league.schedule.last_week == 22
    assert model.pool.size == 156
    assert model.blend.src_k_multiplier["E"] == 0.5
    load_configs()


def test_tov_lower_is_better(league):
    tov = next(c for c in league.categories if c.key == "tov")
    assert tov.higher_is_better is False


def test_canonical_team(league):
    assert league.canonical_team("PHO") == "PHX"
    assert league.canonical_team("ny") == "NYK"
    assert league.canonical_team("CLE") == "CLE"


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError, match="不存在"):
        load_league_config(tmp_path / "nope.yaml")


def test_invalid_yaml_raises(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("league: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError, match="YAML"):
        load_league_config(p)


def test_missing_section_raises(raw_league, write_yaml):
    del raw_league["roster"]
    with pytest.raises(ConfigError, match="roster"):
        load_league_config(write_yaml(raw_league))


def test_extra_field_raises(raw_league, write_yaml):
    raw_league["league"]["leage_id_typo"] = 1
    with pytest.raises(ConfigError, match="leage_id_typo"):
        load_league_config(write_yaml(raw_league))


def test_bad_category_kind_raises(raw_league, write_yaml):
    raw_league["categories"][2]["kind"] = "ratio"
    with pytest.raises(ConfigError):
        load_league_config(write_yaml(raw_league))


def test_percentage_without_components_raises(raw_league, write_yaml):
    del raw_league["categories"][0]["components"]
    with pytest.raises(ConfigError, match="components"):
        load_league_config(write_yaml(raw_league))


def test_prior_columns_mismatch_raises(raw_league, write_yaml):
    del raw_league["prior_columns"]["dd"]
    with pytest.raises(ConfigError, match="prior_columns"):
        load_league_config(write_yaml(raw_league))


def test_active_slot_not_in_slots_raises(raw_league, write_yaml):
    raw_league["roster"]["active_slots"].append("UTIL2")
    with pytest.raises(ConfigError, match="active_slots"):
        load_league_config(write_yaml(raw_league))


def test_unknown_eligibility_position_raises(raw_league, write_yaml):
    raw_league["roster"]["eligibility"]["G"] = ["PG", "GF"]
    with pytest.raises(ConfigError, match="GF"):
        load_league_config(write_yaml(raw_league))


def test_playoff_weeks_gap_raises(raw_league, write_yaml):
    raw_league["schedule"]["playoff_weeks"] = [21, 22, 23]
    with pytest.raises(ConfigError, match="playoff_weeks"):
        load_league_config(write_yaml(raw_league))


def test_bad_date_raises(raw_league, write_yaml):
    raw_league["schedule"]["season_end_date"] = "2027-13-40"
    with pytest.raises(ConfigError, match="season_end_date"):
        load_league_config(write_yaml(raw_league))


def test_punt_overlap_raises(raw_model, write_yaml):
    raw_model["punt"]["never"].append("fg_pct")
    with pytest.raises(ConfigError, match="重疊"):
        load_model_config(write_yaml(raw_model))


def test_missing_src_multiplier_raises(raw_model, write_yaml):
    del raw_model["blend"]["src_k_multiplier"]["E"]
    with pytest.raises(ConfigError, match="src_k_multiplier"):
        load_model_config(write_yaml(raw_model))


def test_wrong_type_raises(raw_model, write_yaml):
    raw_model["pool"]["size"] = "many"
    with pytest.raises(ConfigError, match="size"):
        load_model_config(write_yaml(raw_model))


def test_empty_calibration_bins_raises(raw_model, write_yaml):
    raw_model["backtest"]["calibration_bins"] = []
    with pytest.raises(ConfigError, match="calibration_bins"):
        load_model_config(write_yaml(raw_model))


def test_lowercase_team_alias_raises(raw_league, write_yaml):
    raw_league["team_aliases"]["phx"] = "PHX"
    with pytest.raises(ConfigError, match="大寫"):
        load_league_config(write_yaml(raw_league))


def test_cross_file_unknown_punt_category_raises(league, raw_model, write_yaml):
    raw_model["punt"]["allowed"].append("min")
    model = load_model_config(write_yaml(raw_model))
    with pytest.raises(ConfigError, match="min"):
        validate_consistency(league, model)

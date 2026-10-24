import pandas as pd
import pytest

from fantasy import paths
from fantasy.seeds import SeedDataError, load_draft, load_manual_roster, load_prior


@pytest.fixture(scope="module")
def prior(league):
    return load_prior(league=league)


@pytest.fixture(scope="module")
def draft(league):
    return load_draft(league=league)


def test_prior_count_and_types(prior, league):
    assert len(prior) == 156
    for col in league.prior_columns.values():
        assert pd.api.types.is_float_dtype(prior[col]), col
    assert set(prior["src"]) == {"P", "S", "E"}
    assert prior["prior_rank"].tolist() == list(range(1, 157))


def test_prior_positions_and_teams(prior):
    luka = prior.set_index("player_name").loc["Luka Doncic"]
    assert luka["positions"] == ["PG", "SG"]
    assert not set(prior["nba_team"]) & {"GS", "NO", "NY", "PHO", "SA"}
    assert prior["nba_team"].nunique() == 30


def test_draft_count_and_managers(draft, league):
    assert len(draft) == 132
    counts = draft["manager"].value_counts()
    assert len(counts) == league.league.num_teams
    assert (counts == 11).all()
    assert league.league.my_team_alias_in_draft in counts.index
    assert draft["pick"].tolist() == list(range(1, 133))


def test_draft_teams_share_prior_codes(prior, draft):
    assert set(draft["nba_team"]) <= set(prior["nba_team"])


def test_manual_roster(league):
    roster = load_manual_roster(league=league)
    assert len(roster) == 11
    assert roster["snapshot_date"].nunique() == 1
    lebron = roster.set_index("player_name").loc["LeBron James"]
    assert lebron["gp"] == 2 and lebron["positions"] == ["SF", "PF"]
    assert "進行中" in roster.set_index("player_name").loc["Walker Kessler", "note"]
    assert roster["slot"].value_counts()["C"] == league.roster.slots["C"]


def test_missing_column_raises(tmp_path, league):
    src = paths.prior_path().read_text(encoding="utf-8").splitlines()
    header = src[0].replace(",z_dd", "")
    body = [",".join(line.split(",")[:15] + line.split(",")[16:]) for line in src[1:3]]
    p = tmp_path / "prior.csv"
    p.write_text("\n".join([header, *body]), encoding="utf-8")
    with pytest.raises(SeedDataError, match="z_dd"):
        load_prior(p, league=league)


def test_bad_src_raises(tmp_path, league):
    lines = paths.prior_path().read_text(encoding="utf-8").splitlines()[:3]
    lines[1] = lines[1].replace(",P,", ",X,")
    p = tmp_path / "prior.csv"
    p.write_text("\n".join(lines), encoding="utf-8")
    with pytest.raises(SeedDataError, match="src"):
        load_prior(p, league=league)


def test_non_numeric_price_raises(tmp_path, league):
    lines = paths.draft_path().read_text(encoding="utf-8").splitlines()[:3]
    lines[1] = lines[1].rsplit(",", 1)[0] + ",$24"
    p = tmp_path / "draft.csv"
    p.write_text("\n".join(lines), encoding="utf-8")
    with pytest.raises(SeedDataError, match="price"):
        load_draft(p, league=league)


@pytest.mark.parametrize("n_rows", [1, 3])
def test_unquoted_comma_raises(tmp_path, league, n_rows):
    # 只有一列多欄時 pandas 預設會把第一欄當 index 而不報錯,兩種情況都要擋
    lines = paths.manual_roster_path().read_text(encoding="utf-8").splitlines()[: n_rows + 1]
    lines[1] += "x,y"  # note 欄多出未加引號的逗號
    p = tmp_path / "roster.csv"
    p.write_text("\n".join(lines), encoding="utf-8")
    with pytest.raises(SeedDataError, match="CSV 格式錯誤"):
        load_manual_roster(p, league=league)


def test_missing_file_raises(tmp_path, league):
    with pytest.raises(SeedDataError, match="不存在"):
        load_draft(tmp_path / "nope.csv", league=league)

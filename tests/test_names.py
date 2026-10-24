import pytest

from fantasy.names import is_abbreviated, match_name, name_key, short_key, strip_accents
from fantasy.seeds import load_draft, load_prior


@pytest.fixture(scope="module")
def prior(league):
    return load_prior(league=league)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Nikola Jokić", "nikola jokic"),
        ("Nikola Jokic", "nikola jokic"),
        ("Alperen Şengün", "alperen sengun"),
        ("Jusuf Nurkić", "jusuf nurkic"),
        ("Jaren Jackson Jr.", "jaren jackson"),
        ("Jaren Jackson Jr", "jaren jackson"),
        ("Trey Murphy III", "trey murphy"),
        ("Jimmy Butler III", "jimmy butler"),
        ("P.J. Washington", "pj washington"),
        ("Kel'el Ware", "kelel ware"),
        ("Karl-Anthony Towns", "karl anthony towns"),
        ("  Luka   Dončić ", "luka doncic"),
    ],
)
def test_name_key(raw, expected):
    assert name_key(raw) == expected


def test_strip_accents_non_decomposable():
    assert strip_accents("Łukasz Ødegaard ı") == "Lukasz Odegaard i"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("A. Şengün", ("a", "sengun")),
        ("Alperen Sengun", ("a", "sengun")),
        ("K. Towns", ("k", "towns")),
        ("Karl-Anthony Towns", ("k", "towns")),
        ("S. Gilgeous-Alexander", ("s", "gilgeous alexander")),
        ("Trey Murphy III", ("t", "murphy")),
        ("M. Porter Jr.", ("m", "porter")),
    ],
)
def test_short_key(raw, expected):
    assert short_key(raw) == expected


def test_is_abbreviated():
    assert is_abbreviated("A. Şengün")
    assert is_abbreviated("K. Towns")
    assert not is_abbreviated("P.J. Washington")
    assert not is_abbreviated("Alperen Sengun")


def test_match_full_name_with_diacritics(prior):
    r = match_name("Nikola Jokić", prior)
    assert r.status == "matched" and r.name == "Nikola Jokic"


def test_match_abbreviated_sengun(prior):
    r = match_name("A. Şengün", prior)
    assert r.status == "matched" and r.name == "Alperen Sengun"


def test_match_k_towns(prior):
    assert match_name("K. Towns", prior).name == "Karl-Anthony Towns"


def test_match_suffix_dropped(prior):
    assert match_name("Jimmy Butler", prior).name == "Jimmy Butler III"
    assert match_name("Jaren Jackson", prior).name == "Jaren Jackson Jr."


def test_ambiguous_without_team(prior):
    r = match_name("D. Mitchell", prior)
    assert r.status == "ambiguous"
    assert set(r.candidates) == {"Donovan Mitchell", "Davion Mitchell"}
    assert r.name is None


def test_team_disambiguates(prior):
    assert match_name("D. Mitchell", prior, team="CLE").name == "Donovan Mitchell"
    assert match_name("M. Bridges", prior, team="NYK").name == "Mikal Bridges"
    assert match_name("M. Bridges", prior, team="PHX").name == "Miles Bridges"


def test_team_filter_no_hit_stays_ambiguous(prior):
    r = match_name("D. Mitchell", prior, team="BOS")
    assert r.status == "ambiguous" and len(r.candidates) == 2


def test_single_candidate_team_mismatch_flagged(prior):
    r = match_name("Nikola Jokić", prior, team="LAL")
    assert r.status == "matched" and r.team_mismatch


def test_unmatched(prior):
    assert match_name("Some Rookie", prior).status == "unmatched"
    assert match_name("N. Jokic", prior, team="DEN").name == "Nikola Jokic"
    assert match_name("Nikola Jokovic", prior).status == "unmatched"  # 不做模糊比對


def test_draft_against_prior_sanity(prior, league):
    draft = load_draft(league=league)
    results = {
        row.player_short: match_name(row.player_short, prior, team=row.nba_team) for row in draft.itertuples()
    }
    ambiguous = {k: r.candidates for k, r in results.items() if r.status == "ambiguous"}
    unmatched = sorted(k for k, r in results.items() if r.status == "unmatched")
    assert ambiguous == {}
    assert unmatched == ["K. Filipowski", "K. Maluach", "R. Hachimura", "W. Carter Jr."], unmatched
    for short in ["N. Jokić", "L. Dončić", "A. Şengün", "J. Nurkić"]:
        assert results[short].status == "matched", short

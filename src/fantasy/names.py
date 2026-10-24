"""球員名字正規化與比對。

- name_key: 全名比對用的 key (去變音、小寫、去 Jr./III 後綴、去標點)。
- short_key: (名字首字母, 姓氏 key),用來對縮寫名 "K. Towns"。
- match_name: 只做 key 完全相等,不做模糊比對。多個候選時用 nba_team 消歧,仍多個就回傳 ambiguous。
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

# NFKD 不會拆解的字元
_EXTRA_TRANSLIT = str.maketrans(
    {"ø": "o", "Ø": "O", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ı": "i", "ß": "ss", "æ": "ae", "Æ": "AE"}
)
_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv"})
_ABBREV_RE = re.compile(r"^([A-Za-z])\.\s+(\S.*)$")


def strip_accents(s: str) -> str:
    decomposed = unicodedata.normalize("NFKD", s.translate(_EXTRA_TRANSLIT))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _clean_token(token: str) -> str:
    token = token.replace("-", " ")
    return re.sub(r"[.'’`]", "", token)


def _tokens(name: str) -> list[str]:
    """去變音、小寫、依空白切開,並移除結尾的 Jr./III 等後綴。"""
    tokens = strip_accents(name).lower().replace(",", " ").split()
    while len(tokens) > 2 and tokens[-1].strip(".") in _SUFFIXES:
        tokens.pop()
    return tokens


def _join(tokens: list[str]) -> str:
    return " ".join(" ".join(_clean_token(t) for t in tokens).split())


def name_key(name: str) -> str:
    """'Nikola Jokić' -> 'nikola jokic', 'Jaren Jackson Jr.' -> 'jaren jackson'。"""
    return _join(_tokens(name))


def is_abbreviated(name: str) -> bool:
    """'A. Şengün' 這種「首字母. 姓氏」格式。'P.J. Washington' 不算。"""
    return _ABBREV_RE.match(strip_accents(name).strip()) is not None


def short_key(name: str) -> tuple[str, str]:
    """(首字母, 姓氏 key)。'Karl-Anthony Towns' -> ('k', 'towns'), 'A. Şengün' -> ('a', 'sengun')。"""
    tokens = _tokens(name)
    if len(tokens) < 2:
        return ("", _join(tokens))
    return (tokens[0][0], _join(tokens[1:]))


@dataclass(frozen=True)
class MatchResult:
    status: Literal["matched", "ambiguous", "unmatched"]
    candidates: list[str] = field(default_factory=list)
    team_mismatch: bool = False  # 唯一候選但 nba_team 不同 (可能交易),交給人確認

    @property
    def name(self) -> str | None:
        return self.candidates[0] if self.status == "matched" else None


def match_name(
    query: str,
    candidates: pd.DataFrame,
    team: str | None = None,
    name_col: str = "player_name",
    team_col: str = "nba_team",
) -> MatchResult:
    """在 candidates 中找 query。team 必須已經是正規化後的球隊碼。"""
    names = candidates[name_col]
    if is_abbreviated(query):
        qk = short_key(query)
        hit = candidates[names.map(short_key) == qk]
    else:
        qk = name_key(query)
        hit = candidates[names.map(name_key) == qk]

    if hit.empty:
        return MatchResult("unmatched")
    if len(hit) == 1:
        mismatch = team is not None and hit[team_col].iloc[0] != team
        return MatchResult("matched", [hit[name_col].iloc[0]], team_mismatch=mismatch)
    if team is not None:
        by_team = hit[hit[team_col] == team]
        if len(by_team) == 1:
            return MatchResult("matched", [by_team[name_col].iloc[0]])
        if len(by_team) > 1:
            hit = by_team
    return MatchResult("ambiguous", hit[name_col].tolist())

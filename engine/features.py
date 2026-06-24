from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable

from data.label import LabeledAd


@dataclass(frozen=True)
class CreativeFeatures:
    offer_type: str
    framing: str
    urgency_score: float
    copy_length: int
    has_emoji: bool
    cta_type: str
    numeric_offer_present: bool
    terms: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def extract_features(row: LabeledAd) -> CreativeFeatures:
    ad = row.ad
    text = f"{ad.headline} {ad.body_text}".lower()
    return CreativeFeatures(
        offer_type=_offer_type(text),
        framing=_framing(text),
        urgency_score=_urgency(text),
        copy_length=len((ad.body_text or "").split()),
        has_emoji=any(ord(ch) > 10_000 for ch in ad.body_text + ad.headline),
        cta_type=(ad.cta or "unknown").lower().replace(" ", "_"),
        numeric_offer_present=bool(re.search(r"(£|\$|€|\b\d+[%x]?\b)", text)),
        terms=tuple(_terms(text)),
    )


def feature_rows(rows: Iterable[LabeledAd]) -> list[tuple[LabeledAd, CreativeFeatures]]:
    return [(row, extract_features(row)) for row in rows]


def _offer_type(text: str) -> str:
    if "free bet" in text or "bet £" in text or "bet $" in text:
        return "free_bet"
    if "boost" in text or "super boost" in text:
        return "odds_boost"
    if "insurance" in text or "money back" in text:
        return "bet_insurance"
    if "deposit" in text or "match" in text:
        return "deposit_match"
    return "none"


def _framing(text: str) -> str:
    if any(term in text for term in ["england", "scotland", "wales", "three lions", "national team"]):
        return "national_team"
    if "world cup" in text or "tournament" in text:
        return "world_cup"
    if "back" in text or "miss" in text or "return" in text:
        return "lapsed_winback"
    return "generic"


def _urgency(text: str) -> float:
    score = 0.0
    for term in ["today", "tonight", "now", "limited", "ends", "kick off", "last chance"]:
        if term in text:
            score += 0.2
    return min(score, 1.0)


def _terms(text: str) -> list[str]:
    tokens = re.findall(r"[a-z][a-z0-9]+", text)
    stop = {"the", "and", "for", "with", "your", "you", "now", "new", "get", "bet", "sportsbook"}
    return [tok for tok in tokens if tok not in stop][:40]


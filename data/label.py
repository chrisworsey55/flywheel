from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .schema import Ad


HIGH_IMPRESSION_BUCKETS = {"100K-1M", "1M+"}


@dataclass(frozen=True)
class LabeledAd:
    ad: Ad
    label: int
    label_name: str
    days_running: int

    def to_dict(self) -> dict[str, object]:
        row = self.ad.to_dict()
        row.update({"label": self.label, "label_name": self.label_name, "days_running": self.days_running})
        return row


def label_ad(ad: Ad) -> LabeledAd | None:
    days = ad.days_running
    winner = days >= 60 or ad.impressions_bucket in HIGH_IMPRESSION_BUCKETS
    loser = ad.low_impression_flag or ((not ad.is_active) and days < 14)
    if winner and not loser:
        return LabeledAd(ad=ad, label=1, label_name="WINNER", days_running=days)
    if loser and not winner:
        return LabeledAd(ad=ad, label=0, label_name="LOSER", days_running=days)
    return None


def label_ads(ads: list[Ad], *, print_balance: bool = True) -> list[LabeledAd]:
    labeled = [row for ad in ads if (row := label_ad(ad)) is not None]
    if print_balance:
        counts = Counter(row.label_name for row in labeled)
        print(f"class_balance winners={counts.get('WINNER', 0)} losers={counts.get('LOSER', 0)} dropped={len(ads) - len(labeled)}")
    return labeled


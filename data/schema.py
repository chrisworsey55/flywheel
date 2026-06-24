from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any


IMPRESSION_BUCKETS = ("<1K", "1K-10K", "10K-100K", "100K-1M", "1M+")


@dataclass(frozen=True)
class Ad:
    id: str
    advertiser: str
    market: str
    body_text: str
    headline: str
    cta: str
    link_url: str
    media_type: str
    start_date: str
    last_seen_date: str
    is_active: bool
    impressions_bucket: str
    low_impression_flag: bool
    platforms: list[str]

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "Ad":
        platforms = row.get("platforms", [])
        if isinstance(platforms, str):
            platforms = [part.strip() for part in platforms.replace("|", ",").split(",") if part.strip()]
        return cls(
            id=str(row.get("id") or row.get("ad_archive_id") or row.get("ad_id") or ""),
            advertiser=str(row.get("advertiser") or row.get("page_name") or row.get("brand") or ""),
            market=str(row.get("market") or row.get("country") or "GB"),
            body_text=str(row.get("body_text") or row.get("ad_creative_body") or row.get("copy") or ""),
            headline=str(row.get("headline") or row.get("ad_creative_link_title") or ""),
            cta=str(row.get("cta") or row.get("call_to_action_type") or ""),
            link_url=str(row.get("link_url") or row.get("ad_snapshot_url") or row.get("url") or ""),
            media_type=str(row.get("media_type") or row.get("format") or "unknown"),
            start_date=_date_str(row.get("start_date") or row.get("ad_delivery_start_time")),
            last_seen_date=_date_str(row.get("last_seen_date") or row.get("ad_delivery_stop_time") or row.get("last_seen") or row.get("ad_delivery_start_time")),
            is_active=_as_bool(row.get("is_active") if "is_active" in row else row.get("active", True)),
            impressions_bucket=_bucket(row.get("impressions_bucket") or row.get("impressions")),
            low_impression_flag=_as_bool(row.get("low_impression_flag", False)),
            platforms=list(platforms),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def started(self) -> date:
        return date.fromisoformat(self.start_date)

    @property
    def last_seen(self) -> date:
        return date.fromisoformat(self.last_seen_date)

    @property
    def days_running(self) -> int:
        return max((self.last_seen - self.started).days, 0)


def _date_str(value: Any) -> str:
    if not value:
        return date.today().isoformat()
    text = str(value)[:10]
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date().isoformat()


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "active"}


def _bucket(value: Any) -> str:
    text = str(value or "<1K").upper().replace(",", "").strip()
    if text in {"<1K", "LESS THAN 1K"}:
        return "<1K"
    if text in {"1M+", ">1M", "1000000+"}:
        return "1M+"
    if "100K" in text or "100000" in text:
        return "100K-1M"
    if "10K" in text or "10000" in text:
        return "10K-100K"
    if "1K" in text or "1000" in text:
        return "1K-10K"
    return text if text in IMPRESSION_BUCKETS else "<1K"


def load_ads(path: str) -> list[Ad]:
    import json

    raw = json.loads(open(path, "r", encoding="utf-8").read())
    rows = raw["ads"] if isinstance(raw, dict) and "ads" in raw else raw
    return [Ad.from_dict(row) for row in rows]


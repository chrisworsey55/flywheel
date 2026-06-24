from __future__ import annotations

import argparse
import csv
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .schema import Ad


RAW_DIR = Path(__file__).resolve().parent / "raw"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def normalize_rows(rows: list[dict[str, Any]], brand: str, market: str) -> list[dict[str, Any]]:
    ads: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        merged = {"advertiser": brand, "market": market, **row}
        ad = Ad.from_dict(merged)
        if not ad.id:
            ad = Ad.from_dict({**ad.to_dict(), "id": f"{slug(brand)}_{market.lower()}_{idx:04d}"})
        ads.append(ad.to_dict())
    return ads


def fetch_from_csv(path: Path, brand: str, market: str) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return normalize_rows(rows, brand, market)


def fetch_from_meta_api(brand: str, market: str, token: str) -> list[dict[str, Any]]:
    params = {
        "access_token": token,
        "ad_reached_countries": f'["{market}"]',
        "search_terms": brand,
        "ad_type": "ALL",
        "fields": "id,page_name,ad_creative_body,ad_creative_link_title,ad_delivery_start_time,ad_delivery_stop_time,ad_snapshot_url,publisher_platforms,impressions",
        "limit": "100",
    }
    url = "https://graph.facebook.com/v19.0/ads_archive?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    rows = []
    for item in payload.get("data", []):
        rows.append(
            {
                "id": item.get("id"),
                "advertiser": item.get("page_name", brand),
                "body_text": item.get("ad_creative_body", ""),
                "headline": item.get("ad_creative_link_title", ""),
                "link_url": item.get("ad_snapshot_url", ""),
                "start_date": item.get("ad_delivery_start_time"),
                "last_seen_date": item.get("ad_delivery_stop_time") or item.get("ad_delivery_start_time"),
                "is_active": not bool(item.get("ad_delivery_stop_time")),
                "impressions_bucket": _meta_impression_bucket(item.get("impressions")),
                "platforms": item.get("publisher_platforms", []),
            }
        )
    return normalize_rows(rows, brand, market)


def fetch_from_apify(brand: str, market: str, token: str) -> list[dict[str, Any]]:
    actor = os.environ.get("APIFY_ACTOR", "apify/meta-ad-library-scraper")
    run_url = f"https://api.apify.com/v2/acts/{urllib.parse.quote(actor, safe='')}/run-sync-get-dataset-items?token={token}"
    body = json.dumps({"searchTerms": [brand], "countries": [market], "maxItems": 100}).encode("utf-8")
    request = urllib.request.Request(run_url, data=body, headers={"content-type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        rows = json.loads(response.read().decode("utf-8"))
    return normalize_rows(rows if isinstance(rows, list) else rows.get("items", []), brand, market)


def _meta_impression_bucket(value: Any) -> str:
    if isinstance(value, dict):
        low = int(value.get("lower_bound") or 0)
        high = int(value.get("upper_bound") or low)
        n = max(low, high)
        if n >= 1_000_000:
            return "1M+"
        if n >= 100_000:
            return "100K-1M"
        if n >= 10_000:
            return "10K-100K"
        if n >= 1_000:
            return "1K-10K"
    return "<1K"


def fetch_ads(brand: str, market: str, *, from_csv: str | None = None) -> Path:
    if from_csv:
        ads = fetch_from_csv(Path(from_csv), brand, market)
        backend = "csv"
    elif token := os.environ.get("META_AD_LIBRARY_TOKEN"):
        ads = fetch_from_meta_api(brand, market, token)
        backend = "meta_ad_library_api"
    elif token := os.environ.get("APIFY_TOKEN"):
        ads = fetch_from_apify(brand, market, token)
        backend = "apify"
    else:
        raise SystemExit("No fetch backend available. Set META_AD_LIBRARY_TOKEN, APIFY_TOKEN, or pass --from-csv data/raw/manual.csv.")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / f"{slug(brand)}_{market.lower()}.json"
    out.write_text(json.dumps({"brand": brand, "market": market, "backend": backend, "ads": ads}, indent=2), encoding="utf-8")
    print(json.dumps({"backend": backend, "ads": len(ads), "path": str(out)}, indent=2))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", default=os.environ.get("BRAND", "Fanatics Sportsbook"))
    parser.add_argument("--market", default=os.environ.get("MARKET", "GB"))
    parser.add_argument("--from-csv", default=None)
    args = parser.parse_args()
    fetch_ads(args.brand, args.market, from_csv=args.from_csv)


if __name__ == "__main__":
    main()


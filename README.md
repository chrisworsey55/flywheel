# FLYWHEEL

FLYWHEEL is a self-improving growth-experiment swarm. It studies real ad records, predicts which ads a real advertiser kept alive versus killed, and breeds the hypotheses that predicted fresh holdout reality best.

The validation-honesty claim is the product: the truth labels are not authored by this repo. Labels come from advertiser budget decisions visible in ad-library data: survival duration, active status, and impression scale. Weak results are shown as weak results.

The committed offline sample at `data/raw/fanatics_sportsbook_gb.json` is synthetic generated fixture data, marked with `"synthetic": true`. It exists so `make demo` works without credentials. To reproduce on real data, replace it with a Meta Ad Library/API pull using `make fetch BRAND="Fanatics Sportsbook" MARKET="GB"` or import a CSV with `FROM_CSV=...`.

## How it works

FLYWHEEL is a self-improving growth-experiment swarm. It runs a four-stage loop: STUDY real advertising data (which ads a company kept running vs. killed - un-authored ground truth pulled from the Meta Ad Library), SUGGEST 25 growth experiments per cycle (readable hypotheses about which offers/framings/segments win), RUN each as an out-of-sample prediction (train on older ads, freeze, predict which held-out recent ads survived - no waiting for conversions), and SELF-IMPROVE by breeding the agents whose predictions best matched reality.

The moat is validation honesty: a leakage-free, multiple-testing-deflated evaluator that fails closed and is itself stress-tested ("backtest the backtester") against known-null experiments - so the system can prove which of its own findings are real instead of fooling itself. Self-improvement is measured as rising prediction accuracy on fresh, held-out REAL data - not a number climbing on a function we wrote. Clone it, run `make demo`, and point it at any advertiser with `make fetch BRAND=...`.

## 20-second quickstart

```bash
git clone <repo-url>
cd flywheel
make demo
```

`make demo` runs offline using `data/raw/fanatics_sportsbook_gb.json`, writes `runs/latest.json` and `runs/history.json`, then starts the Next.js dashboard.

Deterministic by default:

```bash
make run SEED=42
```

Randomized draw:

```bash
make run SEED=random
```

## What this is

- A real out-of-sample test against a real advertiser's kept-vs-killed ad decisions.
- A hypothesis swarm that suggests 25 readable growth experiments per cycle.
- A fail-closed evaluator that reports naive score and held-out honest score after multiple-testing deflation.
- A metaevaluation gate that shuffles labels to create known-null experiments; if false-positive rate exceeds 5%, the run halts.
- A compounding loop where self-improvement means holdout prediction accuracy on fresh real ads rising across cycles.

## What this is not

- Not a conversion model.
- Not proof of creative causality.
- Not a source of private platform performance data.
- Survival is a proxy: we infer from budget decisions and impression scale, not conversions.

## Point it at any brand

```bash
make fetch BRAND="Nike" MARKET="GB"
make run BRAND="Nike" MARKET="GB"
```

Fetch backends auto-select in this order:

1. `META_AD_LIBRARY_TOKEN`: Meta Ad Library API. Best for EU/UK where inactive ads are retained long enough to observe killed ads.
2. `APIFY_TOKEN`: Apify Meta Ad Library scraper actor.
3. CSV fallback:

```bash
make fetch BRAND="Nike" MARKET="GB" FROM_CSV=data/raw/manual.csv
```

CSV columns:

`id,advertiser,market,body_text,headline,cta,link_url,media_type,start_date,last_seen_date,is_active,impressions_bucket,low_impression_flag,platforms`

`impressions_bucket` must be one of `<1K`, `1K-10K`, `10K-100K`, `100K-1M`, `1M+`. `platforms` can be comma-separated.

## Label rules

Labels are the only truth:

- `WINNER`: survived at least 60 days, or impressions bucket is at least `100K`.
- `LOSER`: low impression flag, or inactive and ran fewer than 14 days.
- Ambiguous middle is dropped.

Features are extracted from creative fields only: offer type, framing, urgency, copy length, emoji, CTA, numeric offer, and lightweight text terms. The feature extractor never sees the label.

## Dashboard

The dashboard is a Next.js 14 app-router project in `web/`, Tailwind styled, Vercel-deployable, and reads `runs/latest.json` plus `runs/history.json`.

Panels include studied ads, today's experiments, compounding curve, honesty gate, winner's curse, diversity, and a live callout textarea for pasted ad copy. There are no HTML `<form>` tags.

## Run the loop on other substrates

The loop only needs real, un-authored outcome labels:

- App Store or Play rankings over time: which app updates and screenshots survived.
- Pricing or landing-page variants via public web archives: which variants stayed live.
- Job-posting longevity: which roles a company keeps reposting as a real need signal.
- Email subject lines from public newsletter archives: open proxy via repost and promotion.
- Any market with a public kept-vs-killed signal.

## Notes on ATLAS adaptations

Comments mark the adaptation points:

- `engine/diversity.py` adapts the ATLAS Phase B inverse-Simpson N_eff/N breadth fix.
- `engine/evolve.py` adapts Darwinian selection: honest score, novelty pressure, crossover, mutation, cull.
- `engine/evaluator.py` adapts the deflated-score honesty gate from finance lift to ad survival prediction.

## License

MIT.

# Aurum Radar — Data Probe

This directory is a **lightweight data source validation layer** for the MVP phase.

Its sole purpose is to verify whether each configured data source can be:
- Successfully requested
- Parsed for title / links / summary
- Saved as JSON for downstream Agent consumption

> This is NOT the production backend. Once a source is validated here, its
> integration logic migrates to `backend/services/`.

---

## Quick Start

```bash
cd data_probe
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — add API keys (optional; probes skip gracefully if absent)
python scripts/run_all.py
```

---

## Directory Layout

```
data_probe/
├── config/
│   └── sources.yaml          # All data source definitions
├── scripts/
│   ├── utils.py              # Shared HTTP, parsing, output helpers
│   ├── probe_news.py         # News sites
│   ├── probe_competitors.py  # Competitor brand pages
│   ├── probe_platform_policy.py  # Shopee / Lazada policy pages
│   ├── probe_regulations.py  # Government / regulatory sites
│   ├── probe_market_data.py  # GoldAPI + ExchangeRate-API
│   ├── probe_malls.py        # Luxury mall event pages
│   └── run_all.py            # Orchestrator — runs everything
├── output/
│   ├── raw/                  # Raw HTML metadata + extracted links
│   ├── normalized/           # Standardised records (ready for Agent)
│   └── summary_*.json        # Per-run summary report
├── .env.example
└── requirements.txt
```

---

## Running Individual Probes

Each script is standalone:

```bash
python scripts/probe_news.py
python scripts/probe_competitors.py
python scripts/probe_platform_policy.py
python scripts/probe_regulations.py
python scripts/probe_market_data.py
python scripts/probe_malls.py
```

---

## Output Format

Every probe writes two JSON files per run:

**`output/raw/{source_type}_{timestamp}.json`** — raw metadata (HTML length, all extracted links).

**`output/normalized/{source_type}_{timestamp}.json`** — standardised records:

```json
{
  "source_type": "news",
  "market": "Singapore",
  "entity": "Channel News Asia",
  "title": "Gold jewellery demand rises in Q1",
  "summary": null,
  "url": "https://...",
  "published_at": null,
  "fetched_at": "2026-05-21T10:00:00+00:00",
  "status": "success",
  "error": null
}
```

Possible `status` values: `success` | `failed` | `skipped`

---

## Environment Variables

| Variable | Purpose | Required |
|---|---|---|
| `GOLDAPI_API_KEY` | GoldAPI.io gold price | No — skips gracefully |
| `EXCHANGE_RATE_API_KEY` | ExchangeRate-API FX rates | No — skips gracefully |
| `NEWS_API_KEY` | Reserved for NewsAPI.org | No |
| `SERPAPI_API_KEY` | Reserved for SerpAPI | No |
| `FIRECRAWL_API_KEY` | Reserved for Firecrawl | No |
| `REQUEST_TIMEOUT` | HTTP timeout in seconds (default: 15) | No |
| `TAVILY_API_KEY` | Tavily Search (shared with `agent/`) | No — `probe_tavily` skips when missing |
| `REDDIT_CLIENT_ID` | Reddit OAuth (opt-in via `--include reddit`) | No |
| `REDDIT_CLIENT_SECRET` | Reddit OAuth | No |
| `REDDIT_USER_AGENT` | Reddit OAuth UA | No |

---

## Adding a New Source

Edit `config/sources.yaml` and add an entry under the relevant key. The probe
scripts read from YAML — no code changes needed for new URLs.

---

## Global Intelligence Probes (PRD 爬虫2)

Beyond the original SG-focused MVP, `data_probe/` now ships a multi-market
intelligence layer. Targets: **JP / KR / SG / TH / MY / VN / ID / PH / US**.

### Run modes

```bash
python scripts/run_all.py                       # original 6 SG probes (default, unchanged)
python scripts/run_all.py --global              # SG + 5 global probes
python scripts/run_all.py --only-global         # only global probes
python scripts/run_all.py --global --include reddit,trends   # add opt-in social/trend
```

Each global probe is also runnable on its own:

```bash
python scripts/probe_gdelt.py
python scripts/probe_global_news.py
python scripts/probe_federal_register.py
python scripts/probe_tavily.py
python scripts/probe_reddit.py   # opt-in
python scripts/probe_trends.py   # opt-in
```

### Implemented (MVP)

| Probe | Source | Method | Markets |
|---|---|---|---|
| `probe_gdelt` | GDELT 2.0 DOC API | JSON API | all |
| `probe_global_news` | Google News RSS (markets × keywords) | RSS | all |
| `probe_federal_register` | US Federal Register | JSON API | US |
| `probe_tavily` | Tavily Search (ported from `agent/`) | API + 24h file cache | all |

### Opt-in (`--include`)

| Probe | Needs | Default |
|---|---|---|
| `probe_reddit` | `praw` + `REDDIT_CLIENT_ID/SECRET/USER_AGENT` | skipped |
| `probe_trends` | `pytrends` | skipped |

### Registry-only

A larger catalog of sources (Reuters / Nikkei / Korea Herald / NewsAPI /
SEC / FSA / METI / 各国海关 / McKinsey / World Bank …) lives in
`config/sources.yaml:registry_only:` for future implementation. No probe
currently calls them.

### Configuration

- `config/markets.yaml` — 9 markets with Google News `hl/gl/ceid` and `languages`.
- `config/keywords.yaml` — `brands / products / market_topics / platforms / regulation_terms`.
- `config/sources.yaml` — `gdelt / global_news / federal_register / tavily` blocks, plus `registry_only`.

### Output format (PRD §2 unified schema)

Global probes write **JSONL** (one record per line) to
`output/normalized/{source_id}_YYYYMMDD.jsonl`. Each record has 18 fields:

```json
{
  "source_type": "news|social|trend|ecommerce|report|regulation",
  "source_id": "gdelt_doc",
  "source_name": "GDELT 2.0 DOC API",
  "market": "JP|KR|SG|TH|MY|VN|ID|PH|US|GLOBAL",
  "language": "en|ja|ko|th|vi|id|ms",
  "title": "...",
  "url": "...",
  "published_at": "...",
  "collected_at": "...",
  "author_or_account": "...",
  "raw_text": "...",
  "summary": "...",
  "keywords": [],
  "entities": { "brands": [], "competitors": [], "products": [], "locations": [] },
  "signal_type": "competition|product_trend|social_buzz|platform_policy|regulation|macro|consumer_behavior|report",
  "impact_direction": "opportunity|risk|neutral|watch",
  "evidence_level": "official|media|social|third_party_report",
  "confidence": 0.0
}
```

The MVP fills `summary / entities` with rule-based keyword detection (no
LLM dependency). `impact_direction` defaults to `watch`; downstream agent
modules (`agent/`) refine it during analysis.

### Dedup + storage

- Dedup key: `normalized_url` (query string stripped); falls back to
  `sha1(source_name + title + published_at)` when URL is absent.
- Storage: append-only JSONL, one file per `source_id` per UTC date.
- Raw HTML snapshots (`output/raw/{source_id}_{ts}.html`) are saved for
  HTML sources that fail to parse — see `parse_failed` records.

### Compliance notes

- Prefer official APIs / RSS / public web pages.
- Do not bypass logins, paywalls, or anti-bot mechanisms.
- Social media data is fetched only through official APIs or compliant
  third-party services.
- TikTok / Instagram / X access requires platform-side terms compliance;
  these are **registry-only** by default.
- This module collects only public market intelligence; no personal data.

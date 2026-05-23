"""Shared utilities for all probe scripts."""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent
OUTPUT_RAW = ROOT / "output" / "raw"
OUTPUT_NORMALIZED = ROOT / "output" / "normalized"
SOURCES_PATH = ROOT / "config" / "sources.yaml"
MARKETS_PATH = ROOT / "config" / "markets.yaml"
KEYWORDS_PATH = ROOT / "config" / "keywords.yaml"
TAVILY_CACHE_PATH = ROOT / "output" / "tavily_cache.json"
TAVILY_CACHE_TTL_HOURS = 24

OUTPUT_RAW.mkdir(parents=True, exist_ok=True)
OUTPUT_NORMALIZED.mkdir(parents=True, exist_ok=True)

TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))
USER_AGENT = os.getenv("USER_AGENT", "AurumRadarDataProbe/0.1")

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
}


def load_sources() -> dict:
    with open(SOURCES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _fetch_html_urllib(url: str, ua: str | None = None) -> tuple[str | None, str | None]:
    headers = dict(_URLLIB_HEADERS)
    if ua:
        headers["User-Agent"] = ua
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace"), None
    except Exception as e:
        return None, f"urllib:{e}"


def fetch_html(url: str, ua: str | None = None) -> tuple[str | None, str | None]:
    """Fetch a URL and return (html_text, error_message).

    Tries `requests` first; on SSL / connection errors (common on macOS
    LibreSSL + local proxy), automatically falls back to urllib.
    """
    headers = dict(HEADERS)
    if ua:
        headers["User-Agent"] = ua
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.text, None
    except requests.exceptions.Timeout:
        return None, "timeout"
    except requests.exceptions.HTTPError as e:
        return None, f"http_error:{e.response.status_code}"
    except (requests.exceptions.SSLError,
            requests.exceptions.ConnectionError,
            requests.exceptions.ProxyError):
        return _fetch_html_urllib(url, ua=ua)
    except Exception as e:
        return None, str(e)


def fetch_json(url: str, params: dict | None = None,
               ua: str | None = None,
               retries: int = 2,
               backoff: float = 1.5) -> tuple[Any, str | None]:
    """GET a URL via urllib and parse JSON. Returns (data, error).

    Retries on SSL handshake failures (common on LibreSSL + proxy) and
    on 429 with exponential backoff.
    """
    full = url
    if params:
        full = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    headers = dict(_URLLIB_HEADERS)
    headers["Accept"] = "application/json"
    if ua:
        headers["User-Agent"] = ua

    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(full, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body), None
        except json.JSONDecodeError as e:
            return None, f"json_decode:{e}"
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                time.sleep(backoff * (2 ** attempt))
                continue
            return None, f"http_{e.code}"
        except Exception as e:
            last_err = str(e)
            # Retry on transient SSL / connection issues
            if attempt < retries and any(
                tok in last_err for tok in ("EOF", "handshake", "timed out", "timeout", "reset")
            ):
                time.sleep(backoff * (2 ** attempt))
                continue
            return None, last_err
    return None, last_err


def strip_html(text: str) -> str:
    """Strip HTML tags and decode entities. Used for Google News RSS summaries."""
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)


def parse_page_title(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else ""


def extract_links_by_keywords(html: str, base_url: str, keywords: list[str]) -> list[dict]:
    """Return links whose href or text contains any of the keywords (case-insensitive)."""
    soup = BeautifulSoup(html, "lxml")
    results = []
    seen = set()
    kw_lower = [k.lower() for k in keywords]
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(strip=True)
        combined = (href + " " + text).lower()
        if any(kw in combined for kw in kw_lower):
            if href.startswith("http"):
                full = href
            elif href.startswith("/"):
                from urllib.parse import urlparse
                p = urlparse(base_url)
                full = f"{p.scheme}://{p.netloc}{href}"
            else:
                continue
            if full not in seen:
                seen.add(full)
                results.append({"text": text, "url": full})
    return results


def make_record(
    source_type: str,
    market: str,
    entity: str,
    url: str,
    title: str | None = None,
    summary: str | None = None,
    published_at: str | None = None,
    status: str = "success",
    error: str | None = None,
    extra: dict | None = None,
) -> dict:
    record = {
        "source_type": source_type,
        "market": market,
        "entity": entity,
        "title": title,
        "summary": summary,
        "url": url,
        "published_at": published_at,
        "fetched_at": now_iso(),
        "status": status,
        "error": error,
    }
    if extra:
        record.update(extra)
    return record


_URLLIB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def save_outputs(source_type: str, raw: list[dict], normalized: list[dict]) -> None:
    slug = timestamp_slug()
    raw_path = OUTPUT_RAW / f"{source_type}_{slug}.json"
    norm_path = OUTPUT_NORMALIZED / f"{source_type}_{slug}.json"

    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    with open(norm_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)

    print(f"  [saved] raw      → {raw_path.relative_to(ROOT)}")
    print(f"  [saved] normalized → {norm_path.relative_to(ROOT)}")


# =============================================================
# Global intelligence helpers (PRD 爬虫2)
# - markets / keywords config loaders
# - PRD unified record schema
# - JSONL writer with dedupe
# - Tavily file cache (TTL 24h, mirrors agent/cache.py)
# =============================================================

def load_markets() -> dict:
    with open(MARKETS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_keywords() -> dict:
    with open(KEYWORDS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# Default evidence level by source_type, used by make_intelligence_record.
_EVIDENCE_DEFAULTS = {
    "news": "media",
    "social": "social",
    "trend": "third_party_report",
    "ecommerce": "official",
    "report": "third_party_report",
    "regulation": "official",
}


def make_intelligence_record(
    *,
    source_id: str,
    source_name: str,
    source_type: str,
    market: str,
    language: str = "en",
    title: str = "",
    url: str = "",
    published_at: str = "",
    author_or_account: str = "",
    raw_text: str = "",
    summary: str = "",
    keywords: list[str] | None = None,
    brands: list[str] | None = None,
    competitors: list[str] | None = None,
    products: list[str] | None = None,
    locations: list[str] | None = None,
    signal_type: str | None = None,
    impact_direction: str = "watch",
    evidence_level: str | None = None,
    confidence: float = 0.0,
) -> dict:
    """Build a normalized record matching PRD §2 unified schema.

    MVP rule of thumb: callers may leave summary/entities/impact_direction empty;
    use detect_entities() to populate brands/products from raw_text + title.
    """
    return {
        "source_type": source_type,
        "source_id": source_id,
        "source_name": source_name,
        "market": market,
        "language": language,
        "title": title or "",
        "url": url or "",
        "published_at": published_at or "",
        "collected_at": now_iso(),
        "author_or_account": author_or_account or "",
        "raw_text": raw_text or "",
        "summary": summary or "",
        "keywords": list(keywords or []),
        "entities": {
            "brands": list(brands or []),
            "competitors": list(competitors or []),
            "products": list(products or []),
            "locations": list(locations or []),
        },
        "signal_type": signal_type,
        "impact_direction": impact_direction,
        "evidence_level": evidence_level or _EVIDENCE_DEFAULTS.get(source_type, "media"),
        "confidence": float(confidence),
    }


def detect_entities(text: str, kw: dict) -> dict:
    """Cheap keyword-based entity tagging. text = title + summary lower-cased once."""
    low = text.lower()
    hit = {"brands": [], "products": [], "keywords": []}
    for b in kw.get("brands", []):
        if b.lower() in low:
            hit["brands"].append(b)
    for p in kw.get("products", []):
        if p.lower() in low:
            hit["products"].append(p)
    for t in kw.get("market_topics", []):
        if t.lower() in low:
            hit["keywords"].append(t)
    return hit


def dedupe_key(record: dict) -> str:
    """PRD §8 — prefer normalized URL; fallback to hash(source_name+title+published_at)."""
    url = (record.get("url") or "").strip()
    if url:
        # Drop query fragments that Google News uses to track click-throughs.
        parsed = urllib.parse.urlsplit(url)
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    blob = f"{record.get('source_name','')}|{record.get('title','')}|{record.get('published_at','')}"
    return "h:" + hashlib.sha1(blob.encode("utf-8")).hexdigest()


def save_jsonl(source_id: str,
               normalized: list[dict],
               raw: list[dict] | None = None) -> dict:
    """Write normalized + optional raw to JSONL.

    Returns dict of paths + counts. Dedup is applied to `normalized` only.
    """
    date_slug = datetime.now(timezone.utc).strftime("%Y%m%d")
    norm_path = OUTPUT_NORMALIZED / f"{source_id}_{date_slug}.jsonl"

    seen: set[str] = set()
    deduped: list[dict] = []
    for rec in normalized:
        k = dedupe_key(rec)
        if k in seen:
            continue
        seen.add(k)
        deduped.append(rec)

    with open(norm_path, "a", encoding="utf-8") as f:
        for rec in deduped:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    raw_path = None
    if raw:
        raw_path = OUTPUT_RAW / f"{source_id}_{date_slug}.jsonl"
        with open(raw_path, "a", encoding="utf-8") as f:
            for rec in raw:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"  [saved] {norm_path.relative_to(ROOT)}  ({len(deduped)} new, {len(normalized) - len(deduped)} dup)")
    return {
        "normalized_path": str(norm_path),
        "raw_path": str(raw_path) if raw_path else None,
        "saved_count": len(deduped),
        "duplicate_count": len(normalized) - len(deduped),
    }


def save_raw_snapshot(source_id: str, ext: str, content: str) -> str:
    """Dump a raw HTML / text blob to output/raw/ for parse_failed cases."""
    path = OUTPUT_RAW / f"{source_id}_{timestamp_slug()}.{ext}"
    path.write_text(content, encoding="utf-8")
    return str(path.relative_to(ROOT))


# ---------------- Tavily file cache ----------------

def _tavily_cache_load() -> dict:
    if TAVILY_CACHE_PATH.exists():
        try:
            return json.loads(TAVILY_CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _tavily_cache_save(data: dict) -> None:
    TAVILY_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TAVILY_CACHE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def tavily_cache_get(query: str):
    entry = _tavily_cache_load().get(query)
    if not entry:
        return None
    cached_at = datetime.fromisoformat(entry["cached_at"])
    if datetime.now() - cached_at > timedelta(hours=TAVILY_CACHE_TTL_HOURS):
        return None
    return entry["results"]


def tavily_cache_set(query: str, results: list[dict]) -> None:
    data = _tavily_cache_load()
    data[query] = {"results": results, "cached_at": datetime.now().isoformat()}
    _tavily_cache_save(data)


# ---------------- Language helper ----------------

def primary_language(market_code: str, markets_cfg: dict) -> str:
    m = markets_cfg.get(market_code, {})
    langs = m.get("languages") or ["en"]
    return langs[0]

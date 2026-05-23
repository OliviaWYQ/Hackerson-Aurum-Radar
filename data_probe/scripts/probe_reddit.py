"""Reddit social-buzz probe.

Two modes:
  1. **PRAW + OAuth** — used when REDDIT_CLIENT_ID/SECRET/USER_AGENT are set.
     Highest quality (no rate limits, full post body, search across subs).
  2. **Public JSON fallback** — `https://www.reddit.com/r/{sub}/new.json`
     direct urllib hit when creds are missing. Read-only, no OAuth, but
     Reddit aggressively rate-limits unauthenticated traffic. We keep
     request volume low (one /new.json per subreddit) and rely on
     keyword-based filtering in code to surface jewelry-related posts.

Skips if praw missing AND public JSON also fails.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import (  # noqa: E402
    detect_entities,
    load_keywords,
    make_intelligence_record,
    save_jsonl,
)

SUBREDDITS = ["jewelry", "EngagementRings", "Diamonds", "luxury", "watches", "femalefashionadvice"]
TIME_FILTER = "month"
PRAW_SEARCH_LIMIT = 10

# Public JSON mode
PUBLIC_UA = "AurumRadarDataProbe/0.1 (jewelry market intelligence research)"
PUBLIC_LIMIT = 100  # /new.json max is 100
PUBLIC_SLEEP_SEC = 2.0


def _probe_via_praw(kw: dict) -> list[dict]:
    cid = os.environ.get("REDDIT_CLIENT_ID", "").strip()
    csec = os.environ.get("REDDIT_CLIENT_SECRET", "").strip()
    ua = os.environ.get("REDDIT_USER_AGENT", "").strip()

    if not (cid and csec and ua):
        return []
    try:
        import praw
    except ImportError:
        print("  [info] praw not installed — falling back to public JSON")
        return []

    print("  [praw] using authenticated Reddit API")
    reddit = praw.Reddit(client_id=cid, client_secret=csec, user_agent=ua)
    reddit.read_only = True

    queries = list(kw.get("brands", []))[:5] + list(kw.get("products", []))[:5]
    if not queries:
        queries = ["jewelry"]

    raw: list[dict] = []
    normalized: list[dict] = []
    fetched = failed = 0

    for sub in SUBREDDITS:
        for q in queries:
            try:
                subreddit = reddit.subreddit(sub)
                for post in subreddit.search(q, sort="new", time_filter=TIME_FILTER, limit=PRAW_SEARCH_LIMIT):
                    fetched += 1
                    title = post.title or ""
                    body = (post.selftext or "")[:1000]
                    ent = detect_entities(title + " " + body, kw)
                    raw.append({"subreddit": sub, "q": q, "title": title, "url": post.url, "id": post.id})
                    normalized.append(_make_record(sub, title, body,
                                                   permalink=post.permalink,
                                                   author=str(post.author) if post.author else "",
                                                   created_utc=getattr(post, "created_utc", None),
                                                   score=getattr(post, "score", 0),
                                                   num_comments=getattr(post, "num_comments", 0),
                                                   query=q, kw=kw, ent=ent))
            except Exception as e:
                failed += 1
                print(f"    [failed] r/{sub} '{q}' → {e}")

    print(f"  [praw] fetched={fetched} failed={failed}")
    return normalized


def _fetch_subreddit_new(subreddit: str) -> tuple[list[dict], str | None]:
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={PUBLIC_LIMIT}"
    req = urllib.request.Request(url, headers={
        "User-Agent": PUBLIC_UA,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        return [], f"http_{e.code}"
    except Exception as e:
        return [], str(e)

    children = (data.get("data") or {}).get("children") or []
    posts = [c.get("data") or {} for c in children]
    return posts, None


def _probe_via_public_json(kw: dict) -> list[dict]:
    """Read-only fallback: pull /new.json per sub, keyword-filter in code.

    No OAuth needed; uses real UA + sleep to dodge rate limits. We fetch
    100 most-recent posts per subreddit and only keep those whose title or
    body matches any jewelry keyword.
    """
    print("  [public_json] no Reddit creds set — using read-only JSON endpoint")
    brands = [b.lower() for b in kw.get("brands", []) or []]
    products = [p.lower() for p in kw.get("products", []) or []]
    market_topics = [m.lower() for m in kw.get("market_topics", []) or []]
    all_terms = brands + products + market_topics + ["jewelry", "jewellery", "gold", "diamond", "ring"]

    raw: list[dict] = []
    normalized: list[dict] = []
    fetched = failed = filtered = 0

    for i, sub in enumerate(SUBREDDITS):
        if i:
            time.sleep(PUBLIC_SLEEP_SEC)
        posts, err = _fetch_subreddit_new(sub)
        if err:
            failed += 1
            print(f"    [failed] r/{sub} → {err}")
            continue
        fetched += len(posts)
        kept = 0
        for p in posts:
            title = p.get("title", "") or ""
            body = (p.get("selftext", "") or "")[:1500]
            blob = (title + " " + body).lower()
            # r/jewelry / r/Diamonds / r/EngagementRings are intrinsically
            # jewelry subreddits — keep all posts; other subs need a keyword hit.
            sub_lower = sub.lower()
            is_jewelry_sub = sub_lower in ("jewelry", "engagementrings", "diamonds")
            if not is_jewelry_sub and not any(t in blob for t in all_terms):
                continue
            kept += 1
            ent = detect_entities(title + " " + body, kw)
            raw.append({
                "subreddit": sub,
                "title": title,
                "id": p.get("id", ""),
                "permalink": p.get("permalink", ""),
                "score": p.get("score", 0),
                "num_comments": p.get("num_comments", 0),
            })
            normalized.append(_make_record(
                sub, title, body,
                permalink=p.get("permalink", ""),
                author=p.get("author", ""),
                created_utc=p.get("created_utc"),
                score=p.get("score", 0),
                num_comments=p.get("num_comments", 0),
                query="",
                kw=kw,
                ent=ent,
            ))
        filtered += kept
        print(f"    [ok] r/{sub} → fetched={len(posts)} jewelry_relevant={kept}")

    print(f"  [public_json] total fetched={fetched}  relevant={filtered}  failed_subs={failed}")
    return normalized


def _make_record(sub: str, title: str, body: str, *,
                 permalink: str, author: str, created_utc,
                 score: int, num_comments: int,
                 query: str, kw: dict, ent: dict) -> dict:
    pub = ""
    if created_utc:
        try:
            pub = datetime.fromtimestamp(float(created_utc), tz=timezone.utc).isoformat()
        except (TypeError, ValueError):
            pass
    full_url = f"https://www.reddit.com{permalink}" if permalink else ""
    keywords = [query] if query else []
    keywords += ent["keywords"]

    # Confidence proxies social engagement
    score = int(score or 0)
    num_comments = int(num_comments or 0)
    conf = min(0.9, 0.2 + (score / 100.0) * 0.3 + (num_comments / 50.0) * 0.2)

    return make_intelligence_record(
        source_id=f"reddit_{sub}",
        source_name=f"r/{sub}",
        source_type="social",
        market="GLOBAL",
        language="en",
        title=title,
        url=full_url,
        published_at=pub,
        author_or_account=author,
        raw_text=body,
        summary=body[:500],
        keywords=keywords,
        brands=ent["brands"],
        products=ent["products"],
        signal_type="social_buzz",
        impact_direction="watch",
        evidence_level="social",
        confidence=round(conf, 2),
    )


def probe_reddit() -> list[dict]:
    kw = load_keywords()

    # Try PRAW first; fall back to public JSON if missing creds/lib.
    normalized = _probe_via_praw(kw)
    if not normalized:
        normalized = _probe_via_public_json(kw)

    if not normalized:
        print("  [skip] no records from either PRAW or public JSON")
        return []

    info = save_jsonl("reddit", normalized)
    print(f"  source_name        : Reddit")
    print(f"  normalized_count   : {len(normalized)}")
    print(f"  saved_path         : {info['normalized_path']}")
    return normalized


if __name__ == "__main__":
    print("=== probe_reddit ===")
    results = probe_reddit()
    print(f"Done: {len(results)} records")

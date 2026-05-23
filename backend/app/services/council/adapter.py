"""Input adapter — intelligence_events → intelligence_batch (architecture.md §17.5).

Aggregates one market's persisted intelligence_events into the
``intelligence_batch`` shape the council skill's input_schema.json expects.

After the Stage 3 双坐标轴 upgrade (architecture.md §7.3 / preclassify_extract.md):
  * source_category 1:1 maps to input_schema.category (7 values aligned).
  * sentiment is derived from signal_direction; impact_area from impact_scope.
  * env_factors / conduction_chain / intensity / entities / downstream_implications
    / ambiguity_flags are passed through verbatim so experts can reason over
    the full impact mechanism (the "底层影响因子" axis), not only the channel label.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import IntelligenceEvent, MarketSnapshot, RawDocument

# Stage 3 source_category -> input_schema.json category enum.
# council schema category enum: [price, competition, product, regulation, channel,
# consumer, social, macro] —— supply_chain 没有专属类，并入 macro（宏观供给侧）。
_CATEGORY_MAP = {
    "competition": "competition",
    "product": "product",
    "social_media": "social",
    "regulation": "regulation",
    "channel": "channel",
    "macro": "macro",
    "supply_chain": "macro",
    # legacy fallbacks (旧 event_type 值，迁移期间历史数据可能存在)
    "platform": "channel",
    "social": "social",
    "pricing": "price",
    "festival": "consumer",
}

# impact_scope tag -> input_schema.json impact_area enum
# council schema impact_area enum: [product, marketing, channel, pricing, supply, compliance, brand]
# 开放标签 (category_gold / market_CN ...) 放到 tags，不进 impact_area。
_IMPACT_SCOPE_TO_AREA = {
    "brand": "brand",
    "retailer": "channel",
    "consumer": "marketing",
    "raw_material": "supply",
    # category_* 与 market_* 不映射到 impact_area，转入 tags
}

# raw_documents.source_type -> input_schema.json source_type enum
_SOURCE_TYPE_MAP = {
    "news": "news",
    "competitor": "brand_official",
    "platform": "ecommerce",
    "regulation": "regulator",
    "market_data": "report",
    "mall": "other",
    "social": "social",
    "report": "report",
}

# signal_direction -> input_schema.json sentiment enum
_DIRECTION_SENTIMENT = {
    "positive": "positive",
    "negative": "negative",
    "mixed": "neutral",
    "neutral": "neutral",
}

# input_schema source_type values that count as first-party (architecture.md §17.8)
PRIMARY_SOURCES = {"regulator", "brand_official", "report"}


def build_batch(db: Session, market: str) -> dict:
    """Aggregate one market's intelligence_events into an intelligence_batch."""
    events = (
        db.query(IntelligenceEvent)
        .filter(IntelligenceEvent.market == market)
        .order_by(IntelligenceEvent.id)
        .all()
    )
    raw_ids = [e.raw_document_id for e in events if e.raw_document_id]
    raw_map: dict[int, RawDocument] = {}
    if raw_ids:
        rows = db.query(RawDocument).filter(RawDocument.id.in_(raw_ids)).all()
        raw_map = {r.id: r for r in rows}

    items: list[dict] = []
    published: list[datetime] = []
    for e in events:
        extra = e.extra or {}
        raw = raw_map.get(e.raw_document_id)
        pub = raw.published_at if raw else None
        if pub:
            published.append(pub)
        excerpt = ""
        if raw:
            excerpt = (raw.clean_content or raw.raw_content or "")[:200]
        if not excerpt:
            excerpt = (e.key_claim or e.summary or "")[:200]

        category = _CATEGORY_MAP.get(e.source_category or "", "macro")
        sentiment = _DIRECTION_SENTIMENT.get(e.signal_direction or "", "neutral")
        env_factors = e.env_factors or []
        primary_factor = next(
            (f for f in env_factors if isinstance(f, dict) and f.get("is_primary")),
            None,
        )
        scope = list(e.impact_scope or [])
        impact_area, scope_overflow = _split_impact_scope(scope)
        tags = _build_tags(category, env_factors, e.conduction_chain, scope_overflow)

        items.append({
            "id": str(e.id),
            "market": e.market,
            "region": e.region or "",
            "source_type": _SOURCE_TYPE_MAP.get(raw.source_type, "other") if raw else "other",
            "source_name": (raw.source_name if raw else None) or extra.get("source_name") or "",
            "source_url": e.source_url or "",
            "published_at": pub.date().isoformat() if pub else "",
            "category": category,
            "event_summary": e.key_claim or e.summary or e.title or "",
            "raw_excerpt": excerpt,
            "sentiment": sentiment,
            "impact_area": impact_area,
            "confidence": float(e.confidence) if e.confidence is not None else 0.5,
            "tags": tags,
            # --- 底层影响因子层：直接透传 (architecture.md §17.5) ---
            "env_factors": env_factors,
            "primary_env_factor": primary_factor,
            "conduction_chain": e.conduction_chain or None,
            "intensity": e.intensity or 0,
            "entities": e.entities or {},
            "downstream_implications": list(e.downstream_implications or []),
            "ambiguity_flags": list(e.ambiguity_flags or []),
        })

    time_window = ""
    if published:
        lo, hi = min(published).date(), max(published).date()
        time_window = f"{lo.isoformat()}/{hi.isoformat()}"

    return {
        "batch_meta": {
            "market": market,
            "region": (events[0].region if events else "") or "",
            "time_window": time_window,
            "item_count": len(items),
        },
        "items": items,
    }


def _split_impact_scope(scope: list[str]) -> tuple[list[str], list[str]]:
    """Split impact_scope into (impact_area enum subset, overflow tags).

    council input_schema.impact_area is a closed enum; open tags such as
    ``category_gold`` / ``market_CN`` flow into tags instead.
    """
    area: list[str] = []
    overflow: list[str] = []
    for s in scope:
        mapped = _IMPACT_SCOPE_TO_AREA.get(s)
        if mapped:
            if mapped not in area:
                area.append(mapped)
        else:
            overflow.append(s)
    return area, overflow


def _build_tags(
    category: str,
    env_factors: list,
    conduction_chain: dict | None,
    scope_overflow: list[str],
) -> list[str]:
    """tags = env_factor names + conduction_chain.chain_id + category +
    impact_scope overflow (category_*/market_*), deduped.
    """
    tags: list[str] = []
    for f in env_factors or []:
        if isinstance(f, dict) and f.get("factor_name"):
            tags.append(str(f["factor_name"]))
    if isinstance(conduction_chain, dict) and conduction_chain.get("chain_id"):
        tags.append(f"chain_{conduction_chain['chain_id']}")
    if category:
        tags.append(category)
    tags.extend(scope_overflow)
    # dedupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def market_snapshot_context(db: Session, market: str) -> dict:
    """Latest market_snapshot as background context for the council (§17.5)."""
    snapshot = (
        db.query(MarketSnapshot)
        .filter(MarketSnapshot.market == market)
        .order_by(MarketSnapshot.id.desc())
        .first()
    )
    if snapshot is None:
        return {}
    return {
        "opportunity_score": snapshot.opportunity_score,
        "risk_score": snapshot.risk_score,
        "overall_judgement": snapshot.overall_judgement,
        "key_opportunities": snapshot.key_opportunities,
        "key_risks": snapshot.key_risks,
        "watch_items": snapshot.watch_items,
    }


def primary_source_ratio(batch: dict) -> float:
    """Share of items from first-party sources — fed to the synthesis step."""
    items = batch.get("items", [])
    if not items:
        return 0.0
    primary = sum(1 for it in items if it.get("source_type") in PRIMARY_SOURCES)
    return round(primary / len(items), 3)

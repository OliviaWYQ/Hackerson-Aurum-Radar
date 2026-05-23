"""Evaluation agent orchestrator — runs rule checks + LLM critic, produces a
credibility-weighted quality report. Results are returned, not persisted.
"""
from __future__ import annotations

from loguru import logger
from sqlalchemy.orm import Session

from app.models import IntelligenceEvent, RawDocument
from app.services.evaluation.checks import run_rule_checks
from app.services.evaluation.critic import critique_council, critique_event


def _load_events(db: Session, market: str) -> list[dict]:
    rows = (
        db.query(IntelligenceEvent)
        .filter(IntelligenceEvent.market == market)
        .order_by(IntelligenceEvent.id)
        .all()
    )
    out = []
    for e in rows:
        extra = e.extra or {}
        out.append({
            "id": e.id,
            "source_category": e.source_category,
            "title": e.title,
            "summary": e.summary,
            "key_claim": e.key_claim,
            "business_impact": e.business_impact,
            "env_factors": e.env_factors or [],
            "conduction_chain": e.conduction_chain,
            "signal_direction": e.signal_direction,
            "intensity": e.intensity,
            "impact_scope": e.impact_scope or [],
            "downstream_implications": e.downstream_implications or [],
            "ambiguity_flags": e.ambiguity_flags or [],
            "priority": e.priority,
            "confidence": float(e.confidence) if e.confidence is not None else None,
            "opportunity_score": e.opportunity_score,
            "risk_score": e.risk_score,
            "source_url": e.source_url,
            "raw_document_id": e.raw_document_id,
            "credibility_level": extra.get("credibility_level"),
        })
    return out


def _source_excerpts(db: Session, events: list[dict]) -> dict[int, str]:
    ids = [e["raw_document_id"] for e in events if e.get("raw_document_id")]
    if not ids:
        return {}
    rows = (
        db.query(RawDocument.id, RawDocument.clean_content, RawDocument.raw_content)
        .filter(RawDocument.id.in_(ids))
        .all()
    )
    return {i: (clean or raw or "") for i, clean, raw in rows}


def run_evaluation(
    db: Session, market: str, council_report: dict | None = None
) -> dict:
    """Evaluate the agent's output for one market; return a quality report."""
    events = _load_events(db, market)
    logger.info(f"[eval] {market}: evaluating {len(events)} events")
    if not events:
        return {"market": market, "error": "no intelligence_events to evaluate"}

    rule = run_rule_checks(events)

    # per-event evidence grounding (light model, one call per event)
    excerpts = _source_excerpts(db, events)
    verdicts = []
    for e in events:
        c = critique_event(e, excerpts.get(e.get("raw_document_id"), ""))
        verdicts.append({"event_id": e["id"], "title": e["title"], **c})
    grounded = sum(1 for v in verdicts if v.get("verdict") == "grounded")
    cred_ok = sum(1 for v in verdicts if v.get("credibility_ok") is True)

    # holistic council decision-report logic review (reasoning model)
    council_verdict = critique_council(council_report) if council_report else None

    report = {
        "market": market,
        "rule_checks": rule,
        "event_verdicts": verdicts,
        "grounding_pass_rate": round(grounded / len(events), 3),
        "credibility_match_rate": round(cred_ok / len(events), 3),
        "council_logic": council_verdict,
        "human_review_list": _human_review(rule, verdicts),
    }
    report["overall_quality_score"] = _overall_score(report)
    logger.info(f"[eval] {market}: quality score {report['overall_quality_score']}")
    return report


def _human_review(rule: dict, verdicts: list[dict]) -> list[dict]:
    """Items a human should double-check (PRD §16.1 人工复核)."""
    items = list(rule.get("credibility_risk_flags", []))
    for v in verdicts:
        if v.get("verdict") in ("overstated", "unsupported") or v.get("credibility_ok") is False:
            items.append({
                "event_id": v.get("event_id"),
                "title": v.get("title"),
                "issue": f"{v.get('verdict')} — {v.get('issue', '')}",
            })
    return items


def _overall_score(report: dict) -> int:
    """0-100 composite quality score — credibility-weighted."""
    rule = report["rule_checks"]
    n = rule.get("total_events", 1) or 1
    cred_penalty = len(rule.get("credibility_risk_flags", [])) / n
    score = (
        0.20 * rule.get("citation_completeness", 0)
        + 0.15 * rule.get("traceability_rate", 0)
        + 0.35 * report["grounding_pass_rate"]
        + 0.30 * report["credibility_match_rate"]
        - 0.25 * cred_penalty
    )
    return max(0, min(100, round(score * 100)))

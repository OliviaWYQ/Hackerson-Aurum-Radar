"""Rule-based quality checks for the evaluation agent.

Pure logic, no LLM. Credibility is a first-class concern: a high-stakes
conclusion resting on a weak source is the headline failure mode.
"""
from __future__ import annotations

_WEAK_CREDIBILITY = {"C", "unknown", None}


def run_rule_checks(events: list[dict]) -> dict:
    """events: dicts with id / priority / opportunity_score / risk_score /
    source_url / raw_document_id / credibility_level."""
    total = len(events)
    if total == 0:
        return {"total_events": 0}

    with_url = sum(1 for e in events if e.get("source_url"))
    with_fk = sum(1 for e in events if e.get("raw_document_id"))

    cred_dist: dict[str, int] = {}
    for e in events:
        c = e.get("credibility_level") or "unknown"
        cred_dist[c] = cred_dist.get(c, 0) + 1

    # credibility risk — high-stakes events resting on weak sources
    cred_flags = []
    for e in events:
        high_stakes = e.get("priority") == "P0" or (e.get("risk_score") or 0) >= 60
        if high_stakes and e.get("credibility_level") in _WEAK_CREDIBILITY:
            cred_flags.append({
                "event_id": e.get("id"),
                "title": e.get("title"),
                "issue": f"高影响事件（{e.get('priority')} / 风险 {e.get('risk_score')}）"
                         f"仅有低可信来源（{e.get('credibility_level') or 'unknown'}）支撑",
            })

    score_flags = [
        {"event_id": e.get("id"), "issue": "评分越界 0-100"}
        for e in events
        if not (0 <= (e.get("opportunity_score") or 0) <= 100)
        or not (0 <= (e.get("risk_score") or 0) <= 100)
    ]

    return {
        "total_events": total,
        "citation_completeness": round(with_url / total, 3),   # PRD §16.1 引用完整率
        "traceability_rate": round(with_fk / total, 3),        # 事件可回溯 raw_document 比例
        "credibility_distribution": cred_dist,
        "credibility_risk_flags": cred_flags,
        "score_range_flags": score_flags,
    }

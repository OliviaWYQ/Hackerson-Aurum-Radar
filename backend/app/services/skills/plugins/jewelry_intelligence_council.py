from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.skills.base import SkillPlugin


class JewelryIntelligenceCouncilSkill(SkillPlugin):
    """委托适配器：将现有 council 编排器包装为 SkillPlugin。"""

    _skill_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / ".skills" / "jewelry-intelligence-council"

    @property
    def name(self) -> str:
        return "jewelry-intelligence-council"

    @property
    def description(self) -> str:
        return "珠宝海外市场战略情报智囊团：五位专家并行分析 + 总参谋综合，产出可执行的战略决策报告。"

    @property
    def version(self) -> str:
        return "2.0"

    def run(self, input_data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        from app.services.council.orchestrator import run_council

        db = kwargs.get("db")
        market = input_data.get("market") or input_data.get("batch_meta", {}).get("market")
        if not db:
            raise ValueError("Council skill requires 'db' (Session) in kwargs")
        if not market:
            raise ValueError("Council skill requires 'market' in input_data")
        return run_council(db, market)

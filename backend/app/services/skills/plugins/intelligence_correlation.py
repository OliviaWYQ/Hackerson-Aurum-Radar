from pathlib import Path

from app.services.skills.analysis_skill import AnalysisSkill


class IntelligenceCorrelationAnalysisSkill(AnalysisSkill):
    _skill_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / ".skills" / "intelligence-correlation-analysis"

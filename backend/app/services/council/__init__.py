"""Strategic intelligence council — pipeline stage 7 «行动» (architecture.md §17).

Replaces the old services/strategy sandbox and services/action generator.
"""
from app.services.council.actions import derive_actions, normalize_department_actions
from app.services.council.orchestrator import run_council

__all__ = ["run_council", "derive_actions", "normalize_department_actions"]

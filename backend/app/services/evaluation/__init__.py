"""Evaluation agent — a QA pass over the main agent's output.

No ground truth exists (open-info analysis), so 'correctness' = evidence
grounding + logical consistency + credibility soundness. Credibility is
weighted heavily.
"""
from app.services.evaluation.evaluator import run_evaluation

__all__ = ["run_evaluation"]

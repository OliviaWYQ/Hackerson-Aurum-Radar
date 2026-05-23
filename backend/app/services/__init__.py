"""Agent service layer — one sub-package per pipeline stage (architecture.md §9).

Stages: ingestion → extraction → scoring → forecast → brief → action.
The orchestrator lives in app/services/pipeline.py.
"""

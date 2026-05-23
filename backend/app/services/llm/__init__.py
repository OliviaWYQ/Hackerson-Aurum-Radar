"""LLM provider — DashScope (Qwen), OpenAI-compatible (architecture.md §12)."""
from app.services.llm.dashscope import DashScopeLLM, get_llm

__all__ = ["DashScopeLLM", "get_llm"]

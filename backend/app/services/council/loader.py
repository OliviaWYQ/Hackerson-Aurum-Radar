"""Council skill loader — reads the markdown / JSON skill files that define
the jewelry intelligence council (architecture.md §17).

The skill package is vendored under skills/jewelry_intelligence_council/.
Analysis experts are auto-discovered by scanning experts/*.md frontmatter
(role_type: expert vs synthesis) — no hard-coded expert list, no YAML parser.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_SKILL_DIR = Path(__file__).resolve().parent.parent.parent.parent / ".skills" / "jewelry-intelligence-council"
_EXPERTS_DIR = _SKILL_DIR / "references" / "experts"
_PROMPTS_DIR = _SKILL_DIR / "references" / "prompts"
_KNOWLEDGE_DIR = _SKILL_DIR / "references" / "knowledge"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the simple `key: value` YAML frontmatter at the top of a .md file."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    meta: dict[str, str] = {}
    for line in text[3:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta


@lru_cache(maxsize=1)
def load_experts() -> dict[str, dict]:
    """Discover every expert skill by scanning experts/*.md frontmatter.

    Returns {expert_id: {"id", "title", "role_type", "content"}}, ordered by
    filename.
    """
    experts: dict[str, dict] = {}
    for path in sorted(_EXPERTS_DIR.glob("*.md")):
        content = _read(path)
        meta = _parse_frontmatter(content)
        expert_id = meta.get("name") or path.stem
        experts[expert_id] = {
            "id": expert_id,
            "title": meta.get("title", expert_id),
            "role_type": meta.get("role_type", "expert"),
            "content": content,
        }
    return experts


def analysis_experts() -> list[dict]:
    """The parallel-wave experts (role_type == expert)."""
    return [e for e in load_experts().values() if e["role_type"] == "expert"]


def synthesis_expert() -> dict:
    """The chief strategy officer (role_type == synthesis)."""
    for expert in load_experts().values():
        if expert["role_type"] == "synthesis":
            return expert
    raise RuntimeError(
        "council skill: no synthesis expert (role_type: synthesis) found in experts/"
    )


@lru_cache(maxsize=4)
def load_prompt(name: str) -> str:
    """Load a prompt file by stem, e.g. load_prompt('synthesis_prompt')."""
    return _read(_PROMPTS_DIR / f"{name}.md")


@lru_cache(maxsize=1)
def load_strategy_library() -> dict:
    """The 12-strategy 兵法 library (architecture.md §17.4)."""
    return json.loads(_read(_KNOWLEDGE_DIR / "strategy_library.json"))


@lru_cache(maxsize=8)
def load_knowledge(rel_path: str) -> str:
    """Load a vendored knowledge file, e.g. 'sunzi-strategy/SKILL.md'."""
    return _read(_KNOWLEDGE_DIR / rel_path)

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class SkillRunRequest(BaseModel):
    input_data: dict[str, Any]
    options: dict[str, Any] = {}


class SkillRouteRequest(BaseModel):
    message: str
    options: dict[str, Any] = {}


@router.get("/skills")
def list_skills(request: Request):
    registry = request.app.state.skill_registry
    return {"skills": registry.list_skills()}


@router.post("/skills/{skill_name}/run")
def run_skill(skill_name: str, body: SkillRunRequest, request: Request):
    registry = request.app.state.skill_registry
    if registry.get_skill(skill_name) is None:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}")
    try:
        result = registry.run_skill(skill_name, body.input_data, **body.options)
        return {"skill": skill_name, "output": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/skills/route")
def route_skill(body: SkillRouteRequest, request: Request):
    """用 LLM function calling 自动路由到匹配的 skill。"""
    registry = request.app.state.skill_registry
    try:
        return registry.route(body.message, **body.options)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

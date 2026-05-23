from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db

router = APIRouter()


class AgentQuery(BaseModel):
    type: str = Field(..., description="Agent 类型，如 correlation_analysis")
    event_ids: list[int] | None = Field(None, description="指定事件 ID 列表")
    market: str | None = Field(None, description="按市场过滤")
    time_window: dict[str, str] | None = Field(
        None, description="时间窗口 {start, end}，ISO8601 日期"
    )
    options: dict[str, Any] = {}


@router.get("/agents")
def list_agents(request: Request):
    router_obj = request.app.state.agent_router
    return {"agents": router_obj.list_agents()}


@router.post("/agents/dispatch")
def dispatch_agent(body: AgentQuery, request: Request, db: Session = Depends(get_db)):
    router_obj = request.app.state.agent_router
    query = body.model_dump(exclude_none=True, exclude={"options"})
    query.update(body.options)
    try:
        result = router_obj.dispatch(query, db)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class StreamRequest(BaseModel):
    type: str = Field(..., description="Agent 类型，如 correlation_analysis")
    session_id: str | None = Field(None, description="会话 ID，不传则自动创建")
    messages: list[dict[str, str]] | str = Field(
        ..., description="OpenAI 协议消息列表，或纯文本字符串"
    )


def _build_chunk(
    id: str,
    delta: dict[str, Any],
    finish_reason: str | None = None,
    session_id: str | None = None,
) -> str:
    chunk: dict[str, Any] = {
        "id": id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "agent",
        "choices": [
            {"index": 0, "delta": delta, "finish_reason": finish_reason}
        ],
    }
    if session_id is not None:
        chunk["session_id"] = session_id
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


@router.post("/agents/stream")
async def stream_agent(body: StreamRequest, request: Request):
    router_obj = request.app.state.agent_router
    session_mgr = request.app.state.session_manager

    # 校验 agent 是否存在
    agent = router_obj._type_map.get(body.type)
    if agent is None:
        raise HTTPException(
            status_code=400,
            detail=f"未找到 type={body.type} 对应的 Agent，"
            f"可用类型: {list(router_obj._type_map.keys())}",
        )

    # 获取或创建会话
    session = session_mgr.get_or_create(body.session_id, body.type)
    sid = session.session_id

    # 构造 query（事件 ID 从 messages 中提取）
    # 统一转为 OpenAI messages 数组格式
    if isinstance(body.messages, str):
        normalized_messages = [{"role": "user", "content": body.messages}]
    else:
        normalized_messages = body.messages
    query: dict[str, Any] = {"type": body.type, "messages": normalized_messages}

    async def event_stream():
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        def _producer():
            try:
                for sse_line in agent.stream(query, None):
                    # 给每个 chunk 注入 session_id
                    if sse_line.startswith("data: ") and sse_line != "data: [DONE]\n\n":
                        chunk_data = json.loads(sse_line[6:].strip())
                        chunk_data["session_id"] = sid
                        line = f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                    else:
                        line = sse_line
                    queue.put_nowait(line)
            except Exception as exc:
                error_chunk = _build_chunk(
                    "agent-error",
                    {"content": json.dumps({"error": str(exc)}, ensure_ascii=False)},
                    finish_reason="stop",
                    session_id=sid,
                )
                queue.put_nowait(error_chunk)
                queue.put_nowait("data: [DONE]\n\n")
            finally:
                queue.put_nowait(None)

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _producer)

        while True:
            line = await queue.get()
            if line is None:
                break
            yield line

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agents/sessions")
def list_sessions(request: Request):
    session_mgr = request.app.state.session_manager
    sessions = session_mgr.list_sessions()
    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "agent_type": s.agent_type,
                "created_at": s.created_at.isoformat(),
            }
            for s in sessions
        ]
    }

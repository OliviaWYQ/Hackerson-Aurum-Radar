from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentSession:
    session_id: str
    agent_type: str
    created_at: datetime = field(default_factory=datetime.utcnow)


class SessionManager:
    """内存会话管理器 — 仅存元数据，重启丢失。"""

    def __init__(self) -> None:
        self._sessions: dict[str, AgentSession] = {}

    def get_or_create(
        self, session_id: str | None, agent_type: str
    ) -> AgentSession:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        sid = session_id or f"sess-{uuid.uuid4().hex[:12]}"
        session = AgentSession(session_id=sid, agent_type=agent_type)
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> AgentSession | None:
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[AgentSession]:
        return list(self._sessions.values())


_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager

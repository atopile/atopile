from __future__ import annotations

from dataclasses import dataclass

from atopile.dataclasses import AppContext


@dataclass
class AgentExecutionContext(AppContext):
    agent_session_id: str | None = None
    agent_run_id: str | None = None
    agent_scope_root: str | None = None

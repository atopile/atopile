from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    ok: bool
    sessions: int
    pool: int
    max_machine_count: int | None
    uptime: int


class DashboardPoint(BaseModel):
    timestamp_ms: int
    active: int
    warm: int
    total: int


class DashboardSeriesResponse(BaseModel):
    points: list[DashboardPoint]
    active: int
    warm: int
    total: int
    max_machine_count: int | None


class ErrorResponse(BaseModel):
    error: str


class SessionInfo(BaseModel):
    created: int
    last_seen: int
    last_validated: int = Field(default=0)
    replay_state: str = Field(min_length=1)

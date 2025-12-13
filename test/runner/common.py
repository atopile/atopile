from enum import StrEnum, auto
from typing import Dict, Optional

from pydantic import BaseModel

ORCHESTRATOR_URL_ENV = "FBRK_TEST_ORCHESTRATOR_URL"


class Outcome(StrEnum):
    PASSED = auto()
    FAILED = auto()
    ERROR = auto()
    SKIPPED = auto()
    CRASHED = auto()


class EventType(StrEnum):
    START = auto()
    FINISH = auto()
    EXIT = auto()


class ClaimRequest(BaseModel):
    pid: int


class ClaimResponse(BaseModel):
    nodeid: Optional[str]


class EventRequest(BaseModel):
    type: EventType
    pid: int
    timestamp: float
    nodeid: Optional[str] = None
    outcome: Optional[Outcome] = None
    output: Optional[Dict[str, str]] = None
    error_message: Optional[str] = None
    memory_usage_mb: Optional[float] = None
    memory_peak_mb: Optional[float] = None

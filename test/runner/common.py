from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import Dict, Optional

from dataclasses_json import DataClassJsonMixin, config
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


@dataclass
class Report(DataClassJsonMixin):
    @dataclass
    class Summary(DataClassJsonMixin):
        passed: int
        failed: int
        errors: int
        crashed: int
        skipped: int
        total: int
        total_duration: float
        total_summed_duration: float
        total_memory_mb: float
        workers_used: int

    @dataclass
    class Commit(DataClassJsonMixin):
        hash: Optional[str] = None
        short_hash: Optional[str] = None
        author: Optional[str] = None
        message: Optional[str] = None
        time: Optional[str] = None

    @dataclass
    class Ci(DataClassJsonMixin):
        is_ci: bool = False
        run_id: Optional[str] = None
        run_number: Optional[str] = None
        workflow: Optional[str] = None
        job: Optional[str] = None
        runner_name: Optional[str] = None
        runner_os: Optional[str] = None
        actor: Optional[str] = None
        repository: Optional[str] = None
        ref: Optional[str] = None

    @dataclass
    class Test(DataClassJsonMixin):
        file: str
        class_: str = field(metadata=config(field_name="class"))
        function: str
        params: str
        fullnodeid: str
        outcome: str
        duration: float
        error_message: Optional[str] = None
        memory_usage_mb: float = 0.0
        memory_peak_mb: float = 0.0
        worker_pid: Optional[int] = None

    summary: Summary
    commit: Optional[Commit] = None
    ci: Optional[Ci] = None
    tests: list[Test] = field(default_factory=list)

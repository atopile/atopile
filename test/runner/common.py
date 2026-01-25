from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import Any, Dict, Optional

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
    class Run(DataClassJsonMixin):
        start_time: Optional[str] = None
        end_time: Optional[str] = None
        duration_s: float = 0.0
        runner_argv: list[str] = field(default_factory=list)
        pytest_args: list[str] = field(default_factory=list)
        selection_applied: bool = False
        collected_tests: int = 0
        cwd: Optional[str] = None
        hostname: Optional[str] = None
        python_executable: Optional[str] = None
        python_version: Optional[str] = None
        platform: Optional[str] = None
        pytest_version: Optional[str] = None
        report_interval_s: Optional[int] = None
        long_test_threshold_s: Optional[int] = None
        workers_requested: Optional[int] = None
        workers_active: Optional[int] = None
        workers_exited: Optional[int] = None
        generate_html: Optional[bool] = None
        periodic_html: Optional[bool] = None
        baseline_requested: Optional[str] = None
        env: Dict[str, str] = field(default_factory=dict)
        git: Dict[str, Any] = field(default_factory=dict)
        orchestrator_bind: Optional[str] = None
        orchestrator_url: Optional[str] = None
        orchestrator_report_url: Optional[str] = None
        output_limits: Dict[str, Any] = field(default_factory=dict)
        perf: Dict[str, Any] = field(default_factory=dict)

    @dataclass
    class Summary(DataClassJsonMixin):
        passed: int = 0
        failed: int = 0
        errors: int = 0
        crashed: int = 0
        skipped: int = 0
        running: int = 0
        queued: int = 0
        total: int = 0
        collection_errors: int = 0
        regressions: int = 0
        fixed: int = 0
        new_tests: int = 0
        removed: int = 0
        removed_total: int = 0
        baseline_scope: str = "full"
        perf_regressions: int = 0
        perf_improvements: int = 0
        memory_regressions: int = 0
        output_truncated_tests: int = 0
        output_truncated_bytes: int = 0
        progress_percent: int = 0
        total_duration_s: float = 0.0
        total_summed_duration_s: float = 0.0
        total_memory_mb: float = 0.0
        workers_used: int = 0
        duration_percentiles_s: Dict[str, float] = field(default_factory=dict)
        memory_usage_percentiles_mb: Dict[str, float] = field(default_factory=dict)
        memory_peak_percentiles_mb: Dict[str, float] = field(default_factory=dict)

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
    class Baseline(DataClassJsonMixin):
        loaded: bool = False
        commit_hash: Optional[str] = None
        commit_hash_full: Optional[str] = None
        commit_author: Optional[str] = None
        commit_message: Optional[str] = None
        commit_time: Optional[str] = None
        branch: Optional[str] = None
        tests_total: int = 0
        error: Optional[str] = None

    @dataclass
    class CollectionError(DataClassJsonMixin):
        nodeid: str
        error: str
        error_message: Optional[str] = None

    @dataclass
    class Test(DataClassJsonMixin):
        nodeid: str
        file: str
        class_: str = field(metadata=config(field_name="class"))
        function: str
        params: str
        state: str = "queued"
        status: str = "queued"
        outcome: Optional[str] = None
        duration_s: float = 0.0
        duration_human: Optional[str] = None
        start_time: Optional[str] = None
        finish_time: Optional[str] = None
        error_message: Optional[str] = None
        error_type: Optional[str] = None
        error_summary: Optional[str] = None
        output: Optional[Dict[str, str]] = None
        output_full: Optional[Dict[str, str]] = None
        output_meta: Optional[Dict[str, Dict[str, Any]]] = None
        memory_usage_mb: float = 0.0
        memory_peak_mb: float = 0.0
        worker_pid: Optional[int] = None
        worker_id: Optional[int] = None
        worker_log: Optional[str] = None
        compare_status: Optional[str] = None
        baseline_outcome: Optional[str] = None
        baseline_duration_s: Optional[float] = None
        baseline_memory_usage_mb: Optional[float] = None
        baseline_memory_peak_mb: Optional[float] = None
        duration_delta_s: Optional[float] = None
        duration_delta_pct: Optional[float] = None
        speedup_ratio: Optional[float] = None
        speedup_pct: Optional[float] = None
        memory_delta_mb: Optional[float] = None
        memory_delta_pct: Optional[float] = None
        perf_status: Optional[str] = None
        perf_regression: bool = False
        perf_improvement: bool = False
        memory_regression: bool = False
        claim_attempts: int = 0
        requeues: int = 0
        collection_error: bool = False

    schema_version: str = "4"
    generated_at: Optional[str] = None
    run: Run = field(default_factory=Run)
    summary: Summary = field(default_factory=Summary)
    commit: Optional[Commit] = None
    ci: Optional[Ci] = None
    baseline: Optional[Baseline] = None
    collection_errors: list[CollectionError] = field(default_factory=list)
    tests: list[Test] = field(default_factory=list)
    derived: Dict[str, Any] = field(default_factory=dict)
    llm: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)

"""
Build-related Pydantic schemas.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


BuildStatus = Literal["queued", "building", "success", "warning", "failed", "cancelled"]
StageStatus = Literal[
    "pending", "running", "success", "warning", "failed", "error", "skipped"
]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "ALERT"]


class BuildStage(BaseModel):
    """A stage within a build."""

    name: str
    stage_id: str
    display_name: Optional[str] = None
    elapsed_seconds: float = 0.0
    status: StageStatus = "pending"
    infos: int = 0
    warnings: int = 0
    errors: int = 0
    alerts: int = 0


class Build(BaseModel):
    """A build (active, queued, or completed)."""

    # Core identification
    name: str
    display_name: str
    project_name: Optional[str] = None
    build_id: Optional[str] = None

    # Status
    status: BuildStatus = "queued"
    elapsed_seconds: float = 0.0
    warnings: int = 0
    errors: int = 0
    return_code: Optional[int] = None
    error: Optional[str] = None  # Error message from build failure

    # Context
    project_root: Optional[str] = None
    targets: Optional[list[str]] = None
    entry: Optional[str] = None
    started_at: Optional[float] = None

    # Stages and logs
    stages: Optional[list[BuildStage]] = None
    # TODO: Replace this estimate once builds are defined in the graph
    # This is the expected total number of stages for progress calculation
    total_stages: int = 20  # Estimated total stages for progress bar
    log_dir: Optional[str] = None
    log_file: Optional[str] = None

    # Queue info
    queue_position: Optional[int] = None


class BuildRequest(BaseModel):
    """Request to start a build."""

    project_root: str
    targets: list[str] = []  # Empty = all targets
    frozen: bool = False
    # For standalone builds (entry point without ato.yaml build config)
    entry: Optional[str] = None  # e.g., "main.ato:App" - if set, runs standalone build
    standalone: bool = False  # Whether to use standalone mode


class BuildResponse(BaseModel):
    """Response from build request."""

    success: bool
    message: str
    build_id: Optional[str] = None


class BuildStatusResponse(BaseModel):
    """Response for build status."""

    build_id: str
    status: str  # 'queued', 'building', 'success', 'warning', 'failed'
    project_root: str
    targets: list[str]
    return_code: Optional[int] = None
    error: Optional[str] = None


class LogEntry(BaseModel):
    """A single log entry."""

    timestamp: str
    level: LogLevel
    logger: str = ""
    stage: str = ""
    message: str
    ato_traceback: Optional[str] = None
    exc_info: Optional[str] = None


class LogCounts(BaseModel):
    """Log entry counts by level."""

    DEBUG: int = 0
    INFO: int = 0
    WARNING: int = 0
    ERROR: int = 0
    ALERT: int = 0

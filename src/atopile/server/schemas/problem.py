"""
Problem-related Pydantic schemas.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Problem(BaseModel):
    """A problem (error or warning) from a build log."""

    id: str
    level: Literal["error", "warning"]
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    stage: Optional[str] = None
    logger: Optional[str] = None
    build_name: Optional[str] = None
    project_name: Optional[str] = None
    timestamp: Optional[str] = None
    ato_traceback: Optional[str] = None
    exc_info: Optional[str] = None


class ProblemFilter(BaseModel):
    """Filter settings for problems."""

    levels: list[Literal["error", "warning"]] = Field(
        default_factory=lambda: ["error", "warning"]
    )
    build_names: list[str] = Field(default_factory=list)
    stage_ids: list[str] = Field(default_factory=list)


class ProblemsResponse(BaseModel):
    """Response for /api/problems endpoint."""

    problems: list[Problem]
    total: int
    error_count: int
    warning_count: int

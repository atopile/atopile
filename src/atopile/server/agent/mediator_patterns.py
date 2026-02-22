"""Shared regex patterns for the agent mediator modules."""

from __future__ import annotations

import re

_BUILD_ID_RE = re.compile(r"\b[a-f0-9]{8,}\b", re.IGNORECASE)
_AUTOLAYOUT_JOB_ID_RE = re.compile(r"\bal-[a-f0-9]{12}\b", re.IGNORECASE)
_FILE_RE = re.compile(
    r"([A-Za-z0-9_./-]+\.(?:ato|py|md|json|yaml|yml|toml|ts|tsx))"
)
_PDF_FILE_RE = re.compile(r"([A-Za-z0-9_./-]+\.pdf)\b", re.IGNORECASE)
_LCSC_RE = re.compile(r"\bC\d{3,}\b", re.IGNORECASE)
_ENTRY_POINT_RE = re.compile(
    r"([A-Za-z0-9_./-]+\.ato:[A-Za-z_][A-Za-z0-9_]*)"
)
_PACKAGE_RE = re.compile(
    r"\b([a-z0-9_.-]+/[a-z0-9_.-]+)(?:@([^\s]+))?\b",
    re.IGNORECASE,
)

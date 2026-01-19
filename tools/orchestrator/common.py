"""Shared constants and utilities for the orchestrator framework."""

from __future__ import annotations

import os
from pathlib import Path

# Default storage directory (relative to working directory)
DEFAULT_STORAGE_DIR = Path(".orchestrator")

# Subdirectories
SESSIONS_DIR = "sessions"
AGENTS_DIR = "agents"
LOGS_DIR = "logs"
PIPELINES_DIR = "pipelines"
PIPELINE_SESSIONS_DIR = "pipeline_sessions"


def get_storage_dir() -> Path:
    """Get the storage directory, creating it if needed."""
    storage_dir = Path(os.environ.get("ORCHESTRATOR_STORAGE_DIR", DEFAULT_STORAGE_DIR))
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def get_sessions_dir() -> Path:
    """Get the sessions storage directory."""
    sessions_dir = get_storage_dir() / SESSIONS_DIR
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


def get_agents_dir() -> Path:
    """Get the agents storage directory."""
    agents_dir = get_storage_dir() / AGENTS_DIR
    agents_dir.mkdir(parents=True, exist_ok=True)
    return agents_dir


def get_logs_dir() -> Path:
    """Get the logs storage directory."""
    logs_dir = get_storage_dir() / LOGS_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_pipelines_dir() -> Path:
    """Get the pipelines storage directory."""
    pipelines_dir = get_storage_dir() / PIPELINES_DIR
    pipelines_dir.mkdir(parents=True, exist_ok=True)
    return pipelines_dir


def get_pipeline_sessions_dir() -> Path:
    """Get the pipeline sessions storage directory."""
    sessions_dir = get_storage_dir() / PIPELINE_SESSIONS_DIR
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


# Default server configuration
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8765

# Agent defaults
DEFAULT_MAX_TURNS = 100
DEFAULT_TIMEOUT_SECONDS = 3600  # 1 hour

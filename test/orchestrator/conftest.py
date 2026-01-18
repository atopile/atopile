"""Shared fixtures for orchestrator tests."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from tools.orchestrator import (
    AgentBackendType,
    AgentConfig,
    AgentState,
    AgentStatus,
    ProcessManager,
    SessionManager,
)
from tools.orchestrator.core import AgentStateStore, SessionStateStore


@pytest.fixture
def temp_storage_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary storage directory."""
    storage_dir = tmp_path / ".orchestrator"
    storage_dir.mkdir(parents=True)
    (storage_dir / "sessions").mkdir()
    (storage_dir / "agents").mkdir()
    (storage_dir / "logs").mkdir()

    old_env = os.environ.get("ORCHESTRATOR_STORAGE_DIR")
    os.environ["ORCHESTRATOR_STORAGE_DIR"] = str(storage_dir)

    yield storage_dir

    if old_env:
        os.environ["ORCHESTRATOR_STORAGE_DIR"] = old_env
    else:
        os.environ.pop("ORCHESTRATOR_STORAGE_DIR", None)


@pytest.fixture
def agent_store(temp_storage_dir: Path) -> AgentStateStore:
    """Create an agent state store with temp storage."""
    return AgentStateStore(persist=True)


@pytest.fixture
def session_store(temp_storage_dir: Path) -> SessionStateStore:
    """Create a session state store with temp storage."""
    return SessionStateStore(persist=True)


@pytest.fixture
def session_manager(temp_storage_dir: Path) -> SessionManager:
    """Create a session manager with temp storage."""
    return SessionManager(persist=True)


@pytest.fixture
def process_manager() -> Generator[ProcessManager, None, None]:
    """Create a process manager."""
    pm = ProcessManager()
    yield pm
    pm.cleanup_all()


@pytest.fixture
def sample_config() -> AgentConfig:
    """Create a sample agent configuration."""
    return AgentConfig(
        backend=AgentBackendType.CLAUDE_CODE,
        prompt="What is 2+2?",
        max_turns=1,
    )


@pytest.fixture
def sample_agent(sample_config: AgentConfig) -> AgentState:
    """Create a sample agent state."""
    return AgentState(
        config=sample_config,
        status=AgentStatus.PENDING,
    )

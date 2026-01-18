"""Tests for the session manager."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.orchestrator.core.session import SessionManager
from tools.orchestrator.exceptions import SessionNotFoundError
from tools.orchestrator.models import AgentBackendType, SessionStatus


class TestSessionManager:
    """Tests for SessionManager."""

    def test_create_session(self, session_manager: SessionManager):
        """Test creating a session."""
        session = session_manager.create_session(
            backend=AgentBackendType.CLAUDE_CODE,
            working_directory="/tmp",
            initial_prompt="Hello",
        )

        assert session is not None
        assert session.metadata.backend == AgentBackendType.CLAUDE_CODE
        assert session.metadata.working_directory == "/tmp"
        assert session.metadata.initial_prompt == "Hello"
        assert session.status == SessionStatus.ACTIVE

    def test_create_session_with_tags(self, session_manager: SessionManager):
        """Test creating a session with tags."""
        session = session_manager.create_session(
            backend=AgentBackendType.CLAUDE_CODE,
            tags=["test", "demo"],
        )

        assert session.metadata.tags == ["test", "demo"]

    def test_get_session(self, session_manager: SessionManager):
        """Test getting a session."""
        created = session_manager.create_session(
            backend=AgentBackendType.CLAUDE_CODE,
        )

        retrieved = session_manager.get_session(created.metadata.id)
        assert retrieved is not None
        assert retrieved.metadata.id == created.metadata.id

    def test_get_session_not_found(self, session_manager: SessionManager):
        """Test getting a nonexistent session raises error."""
        with pytest.raises(SessionNotFoundError):
            session_manager.get_session("nonexistent")

    def test_get_session_or_none(self, session_manager: SessionManager):
        """Test get_session_or_none returns None for missing."""
        assert session_manager.get_session_or_none("nonexistent") is None

        created = session_manager.create_session(
            backend=AgentBackendType.CLAUDE_CODE,
        )
        assert session_manager.get_session_or_none(created.metadata.id) is not None

    def test_update_session_status(self, session_manager: SessionManager):
        """Test updating session status."""
        session = session_manager.create_session(
            backend=AgentBackendType.CLAUDE_CODE,
        )

        updated = session_manager.update_session(
            session.metadata.id,
            status=SessionStatus.COMPLETED,
        )

        assert updated.status == SessionStatus.COMPLETED

    def test_update_session_backend_id(self, session_manager: SessionManager):
        """Test updating backend session ID."""
        session = session_manager.create_session(
            backend=AgentBackendType.CLAUDE_CODE,
        )

        updated = session_manager.update_session(
            session.metadata.id,
            backend_session_id="backend-123",
        )

        assert updated.metadata.backend_session_id == "backend-123"

    def test_update_session_add_agent(self, session_manager: SessionManager):
        """Test adding an agent to session."""
        session = session_manager.create_session(
            backend=AgentBackendType.CLAUDE_CODE,
        )

        updated = session_manager.update_session(
            session.metadata.id,
            add_agent_id="agent-123",
        )

        assert "agent-123" in updated.agent_runs
        assert updated.last_agent_id == "agent-123"

    def test_update_session_metrics(self, session_manager: SessionManager):
        """Test updating session metrics."""
        session = session_manager.create_session(
            backend=AgentBackendType.CLAUDE_CODE,
        )

        updated = session_manager.update_session(
            session.metadata.id,
            add_turns=5,
            add_cost_usd=0.10,
        )

        assert updated.metadata.total_turns == 5
        assert updated.metadata.total_cost_usd == pytest.approx(0.10)

        # Add more
        updated = session_manager.update_session(
            session.metadata.id,
            add_turns=3,
            add_cost_usd=0.05,
        )

        assert updated.metadata.total_turns == 8
        assert updated.metadata.total_cost_usd == pytest.approx(0.15)

    def test_update_session_not_found(self, session_manager: SessionManager):
        """Test updating nonexistent session raises error."""
        with pytest.raises(SessionNotFoundError):
            session_manager.update_session("nonexistent")

    def test_delete_session(self, session_manager: SessionManager):
        """Test deleting a session."""
        session = session_manager.create_session(
            backend=AgentBackendType.CLAUDE_CODE,
        )

        assert session_manager.delete_session(session.metadata.id) is True
        assert session_manager.get_session_or_none(session.metadata.id) is None

    def test_delete_session_not_found(self, session_manager: SessionManager):
        """Test deleting nonexistent session returns False."""
        assert session_manager.delete_session("nonexistent") is False

    def test_list_sessions(self, session_manager: SessionManager):
        """Test listing sessions."""
        session_manager.create_session(backend=AgentBackendType.CLAUDE_CODE)
        session_manager.create_session(backend=AgentBackendType.CLAUDE_CODE)

        sessions = session_manager.list_sessions()
        assert len(sessions) == 2

    def test_list_sessions_filter_backend(self, session_manager: SessionManager):
        """Test filtering sessions by backend."""
        session_manager.create_session(backend=AgentBackendType.CLAUDE_CODE)

        sessions = session_manager.list_sessions(backend=AgentBackendType.CLAUDE_CODE)
        assert len(sessions) == 1

        sessions = session_manager.list_sessions(backend=AgentBackendType.CODEX)
        assert len(sessions) == 0

    def test_list_sessions_filter_status(self, session_manager: SessionManager):
        """Test filtering sessions by status."""
        session = session_manager.create_session(backend=AgentBackendType.CLAUDE_CODE)
        session_manager.update_session(session.metadata.id, status=SessionStatus.COMPLETED)

        sessions = session_manager.list_sessions(status=SessionStatus.COMPLETED)
        assert len(sessions) == 1

        sessions = session_manager.list_sessions(status=SessionStatus.ACTIVE)
        assert len(sessions) == 0

    def test_list_sessions_filter_tags(self, session_manager: SessionManager):
        """Test filtering sessions by tags."""
        session_manager.create_session(
            backend=AgentBackendType.CLAUDE_CODE,
            tags=["test", "demo"],
        )
        session_manager.create_session(
            backend=AgentBackendType.CLAUDE_CODE,
            tags=["test"],
        )

        sessions = session_manager.list_sessions(tags=["test"])
        assert len(sessions) == 2

        sessions = session_manager.list_sessions(tags=["demo"])
        assert len(sessions) == 1

        sessions = session_manager.list_sessions(tags=["test", "demo"])
        assert len(sessions) == 1

    def test_list_sessions_limit(self, session_manager: SessionManager):
        """Test limiting session list."""
        for _ in range(5):
            session_manager.create_session(backend=AgentBackendType.CLAUDE_CODE)

        sessions = session_manager.list_sessions(limit=3)
        assert len(sessions) == 3

    def test_find_by_backend_session_id(self, session_manager: SessionManager):
        """Test finding session by backend session ID."""
        session = session_manager.create_session(backend=AgentBackendType.CLAUDE_CODE)
        session_manager.update_session(
            session.metadata.id,
            backend_session_id="backend-123",
        )

        found = session_manager.find_by_backend_session_id("backend-123")
        assert found is not None
        assert found.metadata.id == session.metadata.id

        not_found = session_manager.find_by_backend_session_id("nonexistent")
        assert not_found is None

    def test_get_or_create_session_new(self, session_manager: SessionManager):
        """Test get_or_create creates new session."""
        session, created = session_manager.get_or_create_session(
            backend=AgentBackendType.CLAUDE_CODE,
            working_directory="/tmp",
        )

        assert created is True
        assert session is not None

    def test_get_or_create_session_existing(self, session_manager: SessionManager):
        """Test get_or_create finds existing session."""
        original = session_manager.create_session(backend=AgentBackendType.CLAUDE_CODE)
        session_manager.update_session(
            original.metadata.id,
            backend_session_id="backend-123",
        )

        session, created = session_manager.get_or_create_session(
            backend=AgentBackendType.CLAUDE_CODE,
            backend_session_id="backend-123",
        )

        assert created is False
        assert session.metadata.id == original.metadata.id

    def test_count(self, session_manager: SessionManager):
        """Test session count."""
        assert session_manager.count() == 0

        session_manager.create_session(backend=AgentBackendType.CLAUDE_CODE)
        assert session_manager.count() == 1

        session_manager.create_session(backend=AgentBackendType.CLAUDE_CODE)
        assert session_manager.count() == 2

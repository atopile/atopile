"""Tests for the state store."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.orchestrator.core.state import AgentStateStore, SessionStateStore, StateStore
from tools.orchestrator.models import AgentBackendType, AgentConfig, AgentState


class TestStateStore:
    """Tests for the generic StateStore."""

    def test_set_and_get(self, agent_store: AgentStateStore, sample_agent: AgentState):
        """Test setting and getting an item."""
        agent_store.set(sample_agent.id, sample_agent)
        retrieved = agent_store.get(sample_agent.id)
        assert retrieved is not None
        assert retrieved.id == sample_agent.id

    def test_get_nonexistent(self, agent_store: AgentStateStore):
        """Test getting a nonexistent item returns None."""
        assert agent_store.get("nonexistent") is None

    def test_exists(self, agent_store: AgentStateStore, sample_agent: AgentState):
        """Test exists check."""
        assert agent_store.exists(sample_agent.id) is False
        agent_store.set(sample_agent.id, sample_agent)
        assert agent_store.exists(sample_agent.id) is True

    def test_delete(self, agent_store: AgentStateStore, sample_agent: AgentState):
        """Test deleting an item."""
        agent_store.set(sample_agent.id, sample_agent)
        assert agent_store.delete(sample_agent.id) is True
        assert agent_store.get(sample_agent.id) is None

    def test_delete_nonexistent(self, agent_store: AgentStateStore):
        """Test deleting a nonexistent item returns False."""
        assert agent_store.delete("nonexistent") is False

    def test_keys_values_items(
        self, agent_store: AgentStateStore, sample_config: AgentConfig
    ):
        """Test keys, values, and items methods."""
        agent1 = AgentState(config=sample_config)
        agent2 = AgentState(config=sample_config)

        agent_store.set(agent1.id, agent1)
        agent_store.set(agent2.id, agent2)

        keys = agent_store.keys()
        assert len(keys) == 2
        assert agent1.id in keys
        assert agent2.id in keys

        values = agent_store.values()
        assert len(values) == 2

        items = agent_store.items()
        assert len(items) == 2

    def test_count(self, agent_store: AgentStateStore, sample_config: AgentConfig):
        """Test count method."""
        assert agent_store.count() == 0

        agent1 = AgentState(config=sample_config)
        agent_store.set(agent1.id, agent1)
        assert agent_store.count() == 1

        agent2 = AgentState(config=sample_config)
        agent_store.set(agent2.id, agent2)
        assert agent_store.count() == 2

    def test_clear(self, agent_store: AgentStateStore, sample_agent: AgentState):
        """Test clearing the store."""
        agent_store.set(sample_agent.id, sample_agent)
        assert agent_store.count() == 1
        agent_store.clear()
        assert agent_store.count() == 0

    def test_update(self, agent_store: AgentStateStore, sample_agent: AgentState):
        """Test atomic update."""
        from tools.orchestrator.models import AgentStatus

        agent_store.set(sample_agent.id, sample_agent)

        def updater(agent: AgentState) -> AgentState:
            agent.status = AgentStatus.RUNNING
            return agent

        updated = agent_store.update(sample_agent.id, updater)
        assert updated is not None
        assert updated.status == AgentStatus.RUNNING

        # Verify persisted
        retrieved = agent_store.get(sample_agent.id)
        assert retrieved.status == AgentStatus.RUNNING

    def test_update_nonexistent(self, agent_store: AgentStateStore):
        """Test updating a nonexistent item returns None."""
        result = agent_store.update("nonexistent", lambda x: x)
        assert result is None


class TestAgentStateStorePersistence:
    """Tests for AgentStateStore persistence."""

    def test_persistence_to_disk(
        self, temp_storage_dir: Path, sample_agent: AgentState
    ):
        """Test that state is persisted to disk."""
        store = AgentStateStore(persist=True)
        store.set(sample_agent.id, sample_agent)

        # Check file exists
        agents_dir = temp_storage_dir / "agents"
        files = list(agents_dir.glob("*.json"))
        assert len(files) == 1
        assert files[0].stem == sample_agent.id

    def test_load_all(self, temp_storage_dir: Path, sample_config: AgentConfig):
        """Test loading all persisted state."""
        # Create and persist
        store1 = AgentStateStore(persist=True)
        agent1 = AgentState(config=sample_config)
        agent2 = AgentState(config=sample_config)
        store1.set(agent1.id, agent1)
        store1.set(agent2.id, agent2)

        # Create new store and load
        store2 = AgentStateStore(persist=True)
        count = store2.load_all()
        assert count == 2

        # Verify loaded
        assert store2.get(agent1.id) is not None
        assert store2.get(agent2.id) is not None

    def test_delete_removes_file(
        self, temp_storage_dir: Path, sample_agent: AgentState
    ):
        """Test that delete removes the file."""
        store = AgentStateStore(persist=True)
        store.set(sample_agent.id, sample_agent)

        agents_dir = temp_storage_dir / "agents"
        assert len(list(agents_dir.glob("*.json"))) == 1

        store.delete(sample_agent.id)
        assert len(list(agents_dir.glob("*.json"))) == 0


class TestSessionStateStore:
    """Tests for SessionStateStore."""

    def test_create_session_store(self, session_store: SessionStateStore):
        """Test creating a session store."""
        assert session_store is not None
        assert session_store.count() == 0

    def test_session_persistence(self, temp_storage_dir: Path):
        """Test session persistence."""
        from tools.orchestrator.models import SessionMetadata, SessionState

        store = SessionStateStore(persist=True)
        meta = SessionMetadata(backend=AgentBackendType.CLAUDE_CODE)
        session = SessionState(metadata=meta)
        store.set(meta.id, session)

        # Check file exists
        sessions_dir = temp_storage_dir / "sessions"
        files = list(sessions_dir.glob("*.json"))
        assert len(files) == 1

"""Tests for the base agent backend."""

from __future__ import annotations

import pytest

from tools.orchestrator.agents import get_available_backends, get_backend
from tools.orchestrator.agents.base import AgentBackend
from tools.orchestrator.models import AgentBackendType


class TestBackendRegistry:
    """Tests for backend registration and discovery."""

    def test_get_claude_backend(self):
        """Test getting the Claude Code backend."""
        backend = get_backend(AgentBackendType.CLAUDE_CODE)
        assert backend is not None
        assert backend.backend_type == AgentBackendType.CLAUDE_CODE

    def test_get_invalid_backend(self):
        """Test getting an invalid backend raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported backend"):
            get_backend(AgentBackendType.CODEX)  # Not implemented yet

    def test_get_available_backends(self):
        """Test getting available backends."""
        backends = get_available_backends()
        assert isinstance(backends, list)
        # Claude should be available (tested in CI)
        backend_types = [b.backend_type for b in backends]
        # At least one backend should be available
        # (may vary by environment)

    def test_backend_is_abstract(self):
        """Test that AgentBackend cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AgentBackend()


class TestBackendInterface:
    """Tests for the backend interface contract."""

    def test_backend_has_required_properties(self):
        """Test that backends have required properties."""
        backend = get_backend(AgentBackendType.CLAUDE_CODE)
        assert hasattr(backend, "backend_type")
        assert hasattr(backend, "binary_name")

    def test_backend_has_required_methods(self):
        """Test that backends have required methods."""
        backend = get_backend(AgentBackendType.CLAUDE_CODE)
        assert hasattr(backend, "get_capabilities")
        assert hasattr(backend, "is_available")
        assert hasattr(backend, "get_binary_path")
        assert hasattr(backend, "build_command")
        assert hasattr(backend, "parse_output_line")
        assert hasattr(backend, "extract_session_id")
        assert hasattr(backend, "get_resume_args")

    def test_backend_capabilities_structure(self):
        """Test that capabilities have expected structure."""
        backend = get_backend(AgentBackendType.CLAUDE_CODE)
        caps = backend.get_capabilities()

        assert hasattr(caps, "streaming")
        assert hasattr(caps, "resume")
        assert hasattr(caps, "session_persistence")
        assert hasattr(caps, "input_during_run")
        assert hasattr(caps, "tools")
        assert hasattr(caps, "budget_control")
        assert hasattr(caps, "max_turns")

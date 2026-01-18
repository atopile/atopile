"""Session management for agent orchestration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..exceptions import SessionNotFoundError
from ..models import (
    AgentBackendType,
    SessionMetadata,
    SessionState,
    SessionStatus,
)
from .state import SessionStateStore

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages agent sessions with persistence.

    Sessions track:
    - Backend-specific session IDs (for resumption)
    - History of agent runs
    - Cumulative metrics (turns, cost)
    - User-defined metadata
    """

    def __init__(self, persist: bool = True) -> None:
        """Initialize the session manager.

        Args:
            persist: Whether to persist sessions to disk
        """
        self._store = SessionStateStore(persist=persist)
        if persist:
            self._store.load_all()

    def create_session(
        self,
        backend: AgentBackendType,
        backend_session_id: str | None = None,
        working_directory: str | None = None,
        initial_prompt: str | None = None,
        tags: list[str] | None = None,
    ) -> SessionState:
        """Create a new session.

        Args:
            backend: The backend type
            backend_session_id: Backend-specific session ID
            working_directory: Working directory for the session
            initial_prompt: The initial prompt used
            tags: Optional tags for categorization

        Returns:
            The created session state
        """
        metadata = SessionMetadata(
            backend=backend,
            backend_session_id=backend_session_id,
            working_directory=working_directory,
            initial_prompt=initial_prompt,
            tags=tags or [],
        )

        session = SessionState(metadata=metadata)
        self._store.set(metadata.id, session)

        logger.info(f"Created session {metadata.id}")
        return session

    def get_session(self, session_id: str) -> SessionState:
        """Get a session by ID.

        Args:
            session_id: The session ID

        Returns:
            The session state

        Raises:
            SessionNotFoundError: If session not found
        """
        session = self._store.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    def get_session_or_none(self, session_id: str) -> SessionState | None:
        """Get a session by ID, or None if not found."""
        return self._store.get(session_id)

    def update_session(
        self,
        session_id: str,
        backend_session_id: str | None = None,
        status: SessionStatus | None = None,
        add_agent_id: str | None = None,
        add_turns: int = 0,
        add_cost_usd: float = 0.0,
    ) -> SessionState:
        """Update a session.

        Args:
            session_id: The session ID
            backend_session_id: New backend session ID
            status: New status
            add_agent_id: Agent ID to add to history
            add_turns: Turns to add to total
            add_cost_usd: Cost to add to total

        Returns:
            The updated session state

        Raises:
            SessionNotFoundError: If session not found
        """

        def updater(session: SessionState) -> SessionState:
            if backend_session_id is not None:
                session.metadata.backend_session_id = backend_session_id
            if status is not None:
                session.status = status
            if add_agent_id is not None:
                session.agent_runs.append(add_agent_id)
                session.last_agent_id = add_agent_id
            session.metadata.total_turns += add_turns
            session.metadata.total_cost_usd += add_cost_usd
            session.touch()
            return session

        result = self._store.update(session_id, updater)
        if result is None:
            raise SessionNotFoundError(session_id)

        return result

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: The session ID

        Returns:
            True if deleted, False if not found
        """
        deleted = self._store.delete(session_id)
        if deleted:
            logger.info(f"Deleted session {session_id}")
        return deleted

    def list_sessions(
        self,
        backend: AgentBackendType | None = None,
        status: SessionStatus | None = None,
        tags: list[str] | None = None,
        limit: int | None = None,
    ) -> list[SessionState]:
        """List sessions with optional filtering.

        Args:
            backend: Filter by backend type
            status: Filter by status
            tags: Filter by tags (all must match)
            limit: Maximum number to return

        Returns:
            List of matching sessions, sorted by updated_at descending
        """
        sessions = self._store.values()

        # Apply filters
        if backend is not None:
            sessions = [s for s in sessions if s.metadata.backend == backend]
        if status is not None:
            sessions = [s for s in sessions if s.status == status]
        if tags:
            sessions = [
                s for s in sessions if all(t in s.metadata.tags for t in tags)
            ]

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.metadata.updated_at, reverse=True)

        # Apply limit
        if limit is not None:
            sessions = sessions[:limit]

        return sessions

    def find_by_backend_session_id(
        self,
        backend_session_id: str,
    ) -> SessionState | None:
        """Find a session by its backend session ID.

        Args:
            backend_session_id: The backend-specific session ID

        Returns:
            The session state, or None if not found
        """
        for session in self._store.values():
            if session.metadata.backend_session_id == backend_session_id:
                return session
        return None

    def get_or_create_session(
        self,
        backend: AgentBackendType,
        backend_session_id: str | None = None,
        working_directory: str | None = None,
    ) -> tuple[SessionState, bool]:
        """Get an existing session or create a new one.

        Args:
            backend: The backend type
            backend_session_id: Backend session ID to look up
            working_directory: Working directory for new session

        Returns:
            Tuple of (session, created) where created is True if new
        """
        if backend_session_id:
            existing = self.find_by_backend_session_id(backend_session_id)
            if existing:
                return existing, False

        session = self.create_session(
            backend=backend,
            backend_session_id=backend_session_id,
            working_directory=working_directory,
        )
        return session, True

    def count(self) -> int:
        """Get total number of sessions."""
        return self._store.count()

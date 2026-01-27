"""
Shared client-side UI state synchronized across webview panels.

State here is not inherently relevant to the backend — it exists on the
server only so that multiple frontend panels (e.g. sidebar vs. editor
webviews) can stay in sync via the WebSocket event bus.
"""


class ClientState:
    """Thin container for cross-panel UI state."""

    def __init__(self) -> None:
        self.log_view_current_id: str | None = None


client_state = ClientState()


def reset_client_state() -> ClientState:
    """Reset client state (used for tests)."""
    global client_state
    client_state = ClientState()
    return client_state

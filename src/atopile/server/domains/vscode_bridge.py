"""Bridge for backend actions that require VS Code extension capabilities."""

from __future__ import annotations

import json
import uuid
from typing import Any

from websockets.asyncio.server import ServerConnection

VSCODE_ACTIONS = frozenset(
    {
        "vscode.openPanel",
        "vscode.openFile",
        "vscode.browseFolder",
        "vscode.openKicad",
        "vscode.resolveThreeDModel",
        "vscode.log",
    }
)


class VscodeBridge:
    """Track and route backend actions that must execute in the extension host."""

    def __init__(self) -> None:
        self._pending_requests: dict[ServerConnection, dict[str, dict[str, str]]] = {}

    def add_client(self, ws: ServerConnection) -> None:
        self._pending_requests[ws] = {}

    def remove_client(self, ws: ServerConnection) -> None:
        self._pending_requests.pop(ws, None)

    def handles(self, action: str) -> bool:
        return action in VSCODE_ACTIONS

    async def forward_request(
        self, ws: ServerConnection, session_id: str, msg: dict[str, Any]
    ) -> None:
        action = str(msg.get("action", ""))
        request_id = msg.get("requestId")
        if not isinstance(request_id, str) or not request_id:
            request_id = uuid.uuid4().hex

        pending = self._pending_requests.setdefault(ws, {})
        pending.setdefault(session_id, {})[request_id] = action
        payload = {
            key: value for key, value in msg.items() if key not in {"type", "requestId"}
        }
        payload.update(
            {
                "type": "extension_request",
                "sessionId": session_id,
                "requestId": request_id,
                "action": action,
            }
        )
        await ws.send(json.dumps(payload))

    async def handle_response(
        self, ws: ServerConnection, session_id: str, msg: dict[str, Any]
    ) -> None:
        request_id = msg.get("requestId")
        if not isinstance(request_id, str) or not request_id:
            return

        pending_by_session = self._pending_requests.get(ws)
        if pending_by_session is None:
            return

        pending = pending_by_session.get(session_id)
        if pending is None:
            return

        action = pending.pop(request_id, msg.get("action", ""))
        ok = msg.get("ok") is not False
        response = {
            "type": "action_result",
            "sessionId": session_id,
            "requestId": request_id,
            "action": action,
            "ok": ok,
        }
        if ok:
            response["result"] = msg.get("result")
        else:
            response["error"] = msg.get("error") or f"{action} failed"
        await ws.send(json.dumps(response))

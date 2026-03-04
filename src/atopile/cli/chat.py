"""ato chat — talk to the atopile agent from the terminal."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

# ANSI helpers
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_RESET = "\033[0m"
_CLEAR_LINE = "\r\033[K"


def _base(port: int) -> str:
    return f"http://localhost:{port}"


def _ws_url(port: int) -> str:
    return f"ws://localhost:{port}/ws/state"


# ── HTTP helpers (session/run creation, final result fetch) ──────────


def _create_session(base: str, project: str) -> str:
    import requests

    r = requests.post(
        f"{base}/api/agent/sessions",
        json={"projectRoot": project},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["sessionId"]


def _create_run(base: str, sid: str, msg: str, project: str) -> str:
    import requests

    r = requests.post(
        f"{base}/api/agent/sessions/{sid}/runs",
        json={"message": msg, "projectRoot": project, "selectedTargets": []},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["runId"]


def _get_run(base: str, sid: str, rid: str) -> dict:
    import requests

    r = requests.get(
        f"{base}/api/agent/sessions/{sid}/runs/{rid}",
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


# ── WebSocket streaming ─────────────────────────────────────────────


async def _stream_run(ws_url: str, run_id: str) -> None:
    """Connect to the server WebSocket and stream tool progress for a run.

    Returns when the run reaches a terminal phase (done/error/stopped).
    """
    import websockets

    frame = 0
    last_status = ""

    async with websockets.connect(ws_url) as ws:
        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                # No event yet — show spinner with last status
                sym = SPINNER[frame % len(SPINNER)]
                frame += 1
                label = last_status or "thinking…"
                sys.stdout.write(f"{_CLEAR_LINE}{_DIM}{sym} {label}{_RESET}")
                sys.stdout.flush()
                continue
            except websockets.exceptions.ConnectionClosed:
                break

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if msg.get("type") != "event" or msg.get("event") != "agent_progress":
                continue

            data = msg.get("data") or {}
            if data.get("run_id") != run_id:
                continue

            phase = data.get("phase", "")

            if phase == "thinking":
                status = data.get("status_text") or "thinking…"
                detail = data.get("detail_text") or ""
                last_status = f"{status}  {detail}".strip() if detail else status
                sym = SPINNER[frame % len(SPINNER)]
                frame += 1
                sys.stdout.write(f"{_CLEAR_LINE}{_DIM}{sym} {last_status}{_RESET}")
                sys.stdout.flush()

            elif phase == "tool_start":
                name = data.get("name", "?")
                last_status = name
                sym = SPINNER[frame % len(SPINNER)]
                frame += 1
                sys.stdout.write(f"{_CLEAR_LINE}{_DIM}{sym} {name}…{_RESET}")
                sys.stdout.flush()

            elif phase == "tool_end":
                sys.stdout.write(_CLEAR_LINE)
                sys.stdout.flush()
                trace = data.get("trace") or {}
                name = trace.get("name") or data.get("name") or "?"
                ok = trace.get("ok", True)
                icon = f"{_GREEN}✓{_RESET}" if ok else f"{_RED}✗{_RESET}"
                suffix = ""
                if not ok:
                    err = (trace.get("result") or {}).get("error", "")
                    if err:
                        suffix = f"  {_DIM}({err[:80]}){_RESET}"
                print(f"  {icon} {name}{suffix}")
                last_status = ""

            elif phase in ("done", "error", "stopped"):
                sys.stdout.write(_CLEAR_LINE)
                sys.stdout.flush()
                return


def _run_with_streaming(
    base: str, ws_url: str, sid: str, project: str, message: str
) -> bool:
    """Send a message, stream progress via WS, then fetch final result."""
    import requests

    try:
        rid = _create_run(base, sid, message, project)
    except requests.HTTPError as exc:
        detail = exc.response.text[:200] if exc.response is not None else str(exc)
        print(f"{_RED}Error:{_RESET} {detail}")
        return False

    # Stream tool calls in real-time
    try:
        asyncio.run(_stream_run(ws_url, rid))
    except KeyboardInterrupt:
        print(f"\n{_DIM}(interrupted){_RESET}")
        return False

    # Fetch the final result
    data = _get_run(base, sid, rid)
    status = data.get("status", "unknown")

    if status == "completed":
        resp = data.get("response") or {}
        msg = resp.get("assistantMessage", "(no response)")
        print(f"\n{_BOLD}Agent:{_RESET} {msg}\n")
        return True
    elif status == "failed":
        print(f"{_RED}Failed:{_RESET} {data.get('error', 'unknown')}\n")
        return False
    else:
        print(f"Run ended: {status}\n")
        return False


# ── Logs ─────────────────────────────────────────────────────────────


def _dump_logs(session_id: str) -> None:
    try:
        from atopile.model.sqlite import AgentLogs

        AgentLogs.init_db()
        rows = AgentLogs.query_recent(session_id=session_id, limit=30)
    except Exception as exc:
        print(f"  Could not read logs: {exc}")
        return
    if not rows:
        print("  (no entries)")
        return
    for row in rows:
        ts = getattr(row, "timestamp", "?")
        ev = getattr(row, "event", "?")
        tool = getattr(row, "tool_name", "") or ""
        summary = getattr(row, "summary", "") or ""
        line = f"  {_DIM}{ts}{_RESET} {ev}"
        if tool:
            line += f"  tool={tool}"
        if summary:
            line += f"  {summary[:100]}"
        print(line)


# ── REPL ─────────────────────────────────────────────────────────────


def _repl(base: str, ws_url: str, project: str, session_id: str) -> None:
    print(f"{_DIM}Session {session_id[:12]}…  Project: {project}{_RESET}")
    print(f"{_DIM}Commands: /quit  /new  /logs{_RESET}\n")

    while True:
        try:
            user_input = input(f"{_BOLD}You:{_RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input == "/quit":
            break
        if user_input == "/new":
            session_id = _create_session(base, project)
            print(f"{_DIM}New session: {session_id[:12]}…{_RESET}\n")
            continue
        if user_input == "/logs":
            _dump_logs(session_id)
            print()
            continue

        _run_with_streaming(base, ws_url, session_id, project, user_input)


# ── Server check ─────────────────────────────────────────────────────


def _check_server(base: str, port: int, project: str) -> None:
    import requests

    try:
        requests.get(f"{base}/health", timeout=3)
    except requests.ConnectionError:
        typer.echo(
            f"Cannot reach server at {base}.\n"
            f"Start it first:\n\n"
            f"  ato serve backend --port {port} --workspace {project}\n",
            err=True,
        )
        raise typer.Exit(1)


# ── CLI entry point ──────────────────────────────────────────────────


def chat(
    project: Annotated[
        Path,
        typer.Option(
            "--project",
            "-p",
            help="Project root (default: current directory)",
        ),
    ] = Path("."),
    port: Annotated[
        int,
        typer.Option("--port", help="Build server port"),
    ] = 8501,
    message: Annotated[
        Optional[str],
        typer.Option(
            "--message",
            "-m",
            help="Send a single message (non-interactive)",
        ),
    ] = None,
) -> None:
    """Chat with the atopile agent."""
    project_root = str(project.resolve())
    base = _base(port)
    ws = _ws_url(port)

    _check_server(base, port, project_root)
    sid = _create_session(base, project_root)

    if message:
        ok = _run_with_streaming(base, ws, sid, project_root, message)
        raise typer.Exit(0 if ok else 1)

    _repl(base, ws, project_root, sid)

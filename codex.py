from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import typer

UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
ROLLOUT_SESSION_RE = re.compile(
    r"rollout-[^-]+(?:-[^-]+)*-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$",
    re.IGNORECASE,
)

STATE_MAP = {
    "R": "running",
    "S": "sleeping",
    "D": "uninterruptible_sleep",
    "T": "stopped",
    "t": "tracing_stop",
    "Z": "zombie",
    "X": "dead",
    "I": "idle",
}


@dataclass
class CodexProcessInfo:
    pid: int
    ppid: int
    tty: str | None
    cwd: str | None
    session_id: str | None
    git_branch: str | None
    git_dirty: bool | None
    status: str
    cmdline: list[str]
    rollout_path: str | None


app = typer.Typer(add_completion=False, help="Inspect running Codex sessions.")


def read_cmdline(pid: int) -> list[str]:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return []
    return [part for part in raw.decode(errors="ignore").split("\x00") if part]


def read_cwd(pid: int) -> str | None:
    try:
        return os.readlink(f"/proc/{pid}/cwd")
    except OSError:
        return None


def read_tty(pid: int) -> str | None:
    fd0 = Path(f"/proc/{pid}/fd/0")
    try:
        target = os.readlink(fd0)
    except OSError:
        return None
    if target.startswith("/dev/"):
        return target.replace("/dev/", "", 1)
    return target


def read_ppid(pid: int) -> int:
    status_file = Path(f"/proc/{pid}/status")
    try:
        for line in status_file.read_text().splitlines():
            if line.startswith("PPid:"):
                return int(line.split(":", 1)[1].strip())
    except (OSError, ValueError):
        pass
    return -1


def read_state(pid: int) -> str:
    status_file = Path(f"/proc/{pid}/status")
    try:
        for line in status_file.read_text().splitlines():
            if line.startswith("State:"):
                raw = line.split(":", 1)[1].strip()
                code = raw[:1]
                return STATE_MAP.get(code, raw)
    except OSError:
        pass
    return "unknown"


def find_rollout_path(pid: int) -> str | None:
    fd_dir = Path(f"/proc/{pid}/fd")
    try:
        entries = list(fd_dir.iterdir())
    except OSError:
        return None

    for entry in entries:
        try:
            target = os.readlink(entry)
        except OSError:
            continue
        if ".codex/sessions/" in target and target.endswith(".jsonl"):
            if "rollout-" in Path(target).name:
                return target
    return None


def extract_session_id(cmdline: list[str], rollout_path: str | None) -> str | None:
    if rollout_path:
        match = ROLLOUT_SESSION_RE.search(Path(rollout_path).name)
        if match:
            return match.group(1)

    for part in cmdline:
        match = UUID_RE.search(part)
        if match:
            return match.group(0)
    return None


def git_branch_and_dirty(cwd: str | None) -> tuple[str | None, bool | None]:
    if not cwd:
        return None, None

    branch_cmd = ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"]
    branch_proc = subprocess.run(
        branch_cmd, capture_output=True, text=True, check=False
    )
    if branch_proc.returncode != 0:
        return None, None
    branch = branch_proc.stdout.strip() or None

    status_cmd = ["git", "-C", cwd, "status", "--porcelain"]
    status_proc = subprocess.run(
        status_cmd, capture_output=True, text=True, check=False
    )
    if status_proc.returncode != 0:
        return branch, None
    dirty = bool(status_proc.stdout.strip())
    return branch, dirty


def is_codex_backend(cmdline: list[str]) -> bool:
    if not cmdline:
        return False
    exe = cmdline[0]
    return exe.endswith("/codex/codex") or exe == "codex"


def list_codex_processes() -> list[CodexProcessInfo]:
    processes: list[CodexProcessInfo] = []
    for proc_entry in Path("/proc").iterdir():
        if not proc_entry.name.isdigit():
            continue
        pid = int(proc_entry.name)
        cmdline = read_cmdline(pid)
        if not is_codex_backend(cmdline):
            continue

        cwd = read_cwd(pid)
        rollout_path = find_rollout_path(pid)
        session_id = extract_session_id(cmdline, rollout_path)
        branch, dirty = git_branch_and_dirty(cwd)

        processes.append(
            CodexProcessInfo(
                pid=pid,
                ppid=read_ppid(pid),
                tty=read_tty(pid),
                cwd=cwd,
                session_id=session_id,
                git_branch=branch,
                git_dirty=dirty,
                status=read_state(pid),
                cmdline=cmdline,
                rollout_path=rollout_path,
            )
        )

    processes.sort(key=lambda p: (p.cwd or "", p.pid))
    return processes


@app.command()
def main(
    pretty: bool = typer.Option(
        True, "--pretty/--compact", help="Pretty-print JSON output."
    ),
) -> None:
    sessions = [asdict(p) for p in list_codex_processes()]
    output = {"count": len(sessions), "processes": sessions}
    typer.echo(json.dumps(output, indent=2 if pretty else None))


if __name__ == "__main__":
    app()

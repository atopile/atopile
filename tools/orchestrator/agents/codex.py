"""Codex agent backend implementation."""

from __future__ import annotations

import json

from ..models import (
    AgentBackendType,
    AgentCapabilities,
    AgentConfig,
    OutputChunk,
    OutputType,
)
from .base import AgentBackend


class CodexBackend(AgentBackend):
    """Backend for OpenAI Codex CLI.

    Codex is OpenAI's CLI for code generation, providing:
    - JSONL streaming output with --json flag
    - Session persistence and resumption via thread_id
    - Shell command execution (auto-approved with bypass flag)

    Usage:
        codex exec --json "prompt"

    Key differences from Claude Code:
    - Resume is a subcommand: codex exec resume <id>
    - Session ID is called thread_id
    - No system prompt, budget control, max turns, or tool restrictions
    """

    @property
    def backend_type(self) -> AgentBackendType:
        return AgentBackendType.CODEX

    @property
    def binary_name(self) -> str:
        return "codex"

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            streaming=True,
            resume=True,
            session_persistence=True,
            input_during_run=False,
            tools=True,  # Shell commands are tools
            budget_control=False,  # Not supported
            max_turns=False,  # Not supported
            allowed_tools=False,  # Not supported
        )

    def build_command(self, config: AgentConfig) -> list[str]:
        """Build command for codex.

        Key flags:
        - --json: JSONL output to stdout
        - --dangerously-bypass-approvals-and-sandbox: Full access for headless use
        - --skip-git-repo-check: Allow running outside git repos
        - -m, --model: Model selection
        - -C, --cd: Working directory

        Resume is a subcommand: codex exec resume <session_id> [prompt]
        """
        binary_path = self.get_binary_path()
        if binary_path is None:
            raise RuntimeError("Codex binary not found")

        cmd = [str(binary_path), "exec"]

        # Resume handling - it's a subcommand, not a flag
        if config.resume_session and config.session_id:
            cmd.append("resume")
            cmd.append(config.session_id)

        # JSON streaming output
        cmd.append("--json")

        # Full auto mode for headless operation
        cmd.append("--dangerously-bypass-approvals-and-sandbox")

        # Skip git repo check for flexibility
        cmd.append("--skip-git-repo-check")

        # Model selection
        if config.model:
            cmd.extend(["-m", config.model])

        # Working directory
        if config.working_directory:
            cmd.extend(["-C", config.working_directory])

        # Extra args
        if config.extra_args:
            cmd.extend(config.extra_args)

        # Prompt - must be last for non-resume, or after session_id for resume
        if config.prompt:
            cmd.append(config.prompt)

        return cmd

    def parse_output_line(self, line: str, sequence: int) -> OutputChunk | None:
        """Parse Codex JSONL output.

        Codex events:
        - thread.started: {"type":"thread.started","thread_id":"..."}
        - turn.started: {"type":"turn.started"}
        - turn.completed: {"type":"turn.completed","usage":{...}}
        - turn.failed: {"type":"turn.failed","error":{"message":"..."}}
        - error: {"type":"error","message":"..."}
        - item.started: {"type":"item.started","item":{"type":"command_execution",...}}
        - item.completed: {"type":"item.completed","item":{"type":"agent_message"|"reasoning"|"command_execution",...}}
        """
        line = line.strip()
        if not line:
            return None

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return OutputChunk(
                type=OutputType.RAW,
                content=line,
                raw_line=line,
                sequence=sequence,
            )

        event_type = data.get("type", "")

        # Map Codex events to OutputChunk types
        if event_type == "thread.started":
            return OutputChunk(
                type=OutputType.INIT,
                content=None,
                data=data,
                raw_line=line,
                sequence=sequence,
            )
        elif event_type == "turn.started":
            return OutputChunk(
                type=OutputType.STREAM_START,
                content=None,
                data=data,
                raw_line=line,
                sequence=sequence,
            )
        elif event_type == "turn.completed":
            return OutputChunk(
                type=OutputType.RESULT,
                content=None,
                data=data,
                raw_line=line,
                sequence=sequence,
            )
        elif event_type in ("turn.failed", "error"):
            error_msg = data.get("error", {}).get("message") or data.get("message")
            return OutputChunk(
                type=OutputType.ERROR,
                content=error_msg,
                data=data,
                raw_line=line,
                sequence=sequence,
            )
        elif event_type == "item.completed":
            item = data.get("item", {})
            item_type = item.get("type", "")

            if item_type == "reasoning":
                # Model thinking - treat as assistant text
                return OutputChunk(
                    type=OutputType.ASSISTANT,
                    content=item.get("text"),
                    data=data,
                    raw_line=line,
                    sequence=sequence,
                )
            elif item_type == "agent_message":
                return OutputChunk(
                    type=OutputType.ASSISTANT,
                    content=item.get("text"),
                    data=data,
                    raw_line=line,
                    sequence=sequence,
                )
            elif item_type == "command_execution":
                # Shell command completed - map to tool_result
                return OutputChunk(
                    type=OutputType.TOOL_RESULT,
                    content=item.get("aggregated_output"),
                    tool_name="shell",
                    tool_input={"command": item.get("command")},
                    tool_result=item.get("aggregated_output"),
                    is_error=item.get("exit_code", 0) != 0,
                    data=data,
                    raw_line=line,
                    sequence=sequence,
                )
        elif event_type == "item.started":
            item = data.get("item", {})
            if item.get("type") == "command_execution":
                # Shell command starting - map to tool_use
                return OutputChunk(
                    type=OutputType.TOOL_USE,
                    content=item.get("command"),
                    tool_name="shell",
                    tool_input={"command": item.get("command")},
                    data=data,
                    raw_line=line,
                    sequence=sequence,
                )

        # Unknown event type - return as raw
        return OutputChunk(
            type=OutputType.RAW,
            content=str(data),
            data=data,
            raw_line=line,
            sequence=sequence,
        )

    def extract_session_id(self, chunk: OutputChunk) -> str | None:
        """Extract thread_id from Codex output.

        Codex uses thread_id instead of session_id.
        """
        if chunk.data is None:
            return None
        return chunk.data.get("thread_id")

    def get_resume_args(self, session_id: str) -> list[str]:
        """Resume args for Codex are handled in build_command.

        Codex uses a subcommand pattern (codex exec resume <id>) rather than
        a flag, so this returns empty and build_command handles the logic.
        """
        return []

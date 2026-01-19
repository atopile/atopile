"""Claude Code agent backend implementation."""

from __future__ import annotations

from ..models import (
    AgentBackendType,
    AgentCapabilities,
    AgentConfig,
    ClaudeCodeMessage,
    OutputChunk,
    OutputType,
)
from .base import AgentBackend


class ClaudeCodeBackend(AgentBackend):
    """Backend for Claude Code CLI (claude-code / claude).

    Claude Code is the official CLI for Claude, providing:
    - Headless mode with JSON streaming output
    - Session persistence and resumption
    - Tool restrictions
    - Budget controls
    - Max turn limits

    Usage:
        claude -p "prompt" --output-format stream-json
    """

    @property
    def backend_type(self) -> AgentBackendType:
        return AgentBackendType.CLAUDE_CODE

    @property
    def binary_name(self) -> str:
        return "claude"

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            streaming=True,
            resume=True,
            session_persistence=True,
            input_during_run=False,  # Stdin closed; questions handled via session resume
            tools=True,
            budget_control=True,
            max_turns=True,
            allowed_tools=True,
        )

    def build_command(self, config: AgentConfig) -> list[str]:
        """Build command for claude-code.

        Key flags:
        - -p, --print: Non-interactive mode, output result and exit
        - --output-format stream-json: JSON streaming output
        - --resume <id>: Resume a specific session
        - --continue: Continue most recent session
        - --session-id <uuid>: Use specific session ID
        - --max-turns <n>: Limit turns
        - --max-budget-usd <n>: Limit cost
        - --allowedTools <tools>: Comma-separated list of allowed tools
        - --disallowedTools <tools>: Comma-separated list of disallowed tools
        - --model <model>: Model to use
        - --system-prompt <prompt>: System prompt
        """
        binary_path = self.get_binary_path()
        if binary_path is None:
            raise RuntimeError("Claude Code binary not found")

        cmd = [str(binary_path)]

        # Non-interactive mode with JSON streaming
        # Note: stream-json requires --verbose flag
        # --include-partial-messages enables token-level streaming
        cmd.extend(["-p", config.prompt])
        cmd.extend(["--output-format", "stream-json"])
        cmd.append("--verbose")
        cmd.append("--include-partial-messages")

        # Use bypassPermissions for headless operation
        # AskUserQuestion tool calls are captured and can be responded to via the MCP bridge
        # or by resuming the session with the user's answer
        cmd.extend(["--permission-mode", "bypassPermissions"])

        # Session handling
        if config.resume_session and config.session_id:
            cmd.extend(["--resume", config.session_id])
        elif config.session_id:
            cmd.extend(["--session-id", config.session_id])

        # Limits
        if config.max_turns is not None:
            cmd.extend(["--max-turns", str(config.max_turns)])

        if config.max_budget_usd is not None:
            cmd.extend(["--max-budget-usd", str(config.max_budget_usd)])

        # Tool restrictions
        if config.allowed_tools:
            cmd.extend(["--allowedTools", ",".join(config.allowed_tools)])

        if config.disallowed_tools:
            cmd.extend(["--disallowedTools", ",".join(config.disallowed_tools)])

        # Model selection
        if config.model:
            cmd.extend(["--model", config.model])

        # System prompt
        if config.system_prompt:
            cmd.extend(["--system-prompt", config.system_prompt])

        # MCP config for bridge communication
        # NOTE: We do NOT use --mcp-config flag as it causes Claude CLI to hang.
        # Instead, the bridge MCP server should be configured at the project level
        # (in .claude/settings.local.json or ~/.claude.json) and we pass environment
        # variables (AGENT_NAME, PIPELINE_ID, BRIDGE_URL) through the process environment.
        # The bridge MCP server reads these env vars to identify itself.

        # Extra args (user-provided)
        if config.extra_args:
            cmd.extend(config.extra_args)

        return cmd

    def parse_output_line(self, line: str, sequence: int) -> OutputChunk | None:
        """Parse a line of JSON output from claude-code.

        Claude code with --output-format stream-json outputs one JSON object per line.
        Each object has a 'type' field indicating the message type.
        """
        line = line.strip()
        if not line:
            return None

        # Try to parse as JSON message
        msg = ClaudeCodeMessage.from_json_line(line)
        if msg is not None:
            chunk = msg.to_output_chunk(sequence=sequence)
            if chunk is not None:
                chunk.raw_line = line
                return chunk
            return None  # Skip this event

        # If not valid JSON, treat as raw output
        return OutputChunk(
            type=OutputType.RAW,
            content=line,
            raw_line=line,
            sequence=sequence,
        )

    def extract_session_id(self, chunk: OutputChunk) -> str | None:
        """Extract session ID from an output chunk.

        Session ID is typically present in 'init' or 'system' type messages.
        """
        if chunk.data is None:
            return None

        # Look for session_id in the raw data
        return chunk.data.get("session_id")

    def get_resume_args(self, session_id: str) -> list[str]:
        """Get arguments for resuming a claude-code session."""
        return ["--resume", session_id]

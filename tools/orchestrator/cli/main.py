"""CLI interface for the orchestrator."""

from __future__ import annotations

import json
import time
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..agents import get_available_backends, get_backend
from ..common import DEFAULT_HOST, DEFAULT_PORT
from ..core import AgentStateStore, ProcessManager, SessionManager
from ..models import AgentBackendType, AgentConfig, AgentState, AgentStatus

app = typer.Typer(
    name="orchestrator",
    help="Agent orchestration framework for AI coding assistants",
    no_args_is_help=True,
)

console = Console()


@app.command()
def serve(
    host: str = typer.Option(DEFAULT_HOST, "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(DEFAULT_PORT, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
    log_level: str = typer.Option("info", "--log-level", "-l", help="Log level"),
):
    """Start the orchestrator API server."""
    import uvicorn

    console.print(f"[bold green]Starting orchestrator server on {host}:{port}[/]")
    console.print(f"[dim]API docs: http://{host}:{port}/docs[/]")
    console.print("[dim]Press Ctrl+C to stop[/]")

    uvicorn.run(
        "tools.orchestrator.server.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


@app.command()
def spawn(
    prompt: str = typer.Argument(..., help="Prompt to send to the agent"),
    backend: str = typer.Option(
        "claude-code",
        "--backend",
        "-b",
        help="Agent backend to use",
    ),
    max_turns: Optional[int] = typer.Option(
        None,
        "--max-turns",
        "-t",
        help="Maximum number of turns",
    ),
    max_budget: Optional[float] = typer.Option(
        None,
        "--max-budget",
        help="Maximum budget in USD",
    ),
    working_dir: Optional[str] = typer.Option(
        None,
        "--working-dir",
        "-w",
        help="Working directory for the agent",
    ),
    follow: bool = typer.Option(
        True,
        "--follow/--no-follow",
        "-f",
        help="Follow agent output",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output as JSON",
    ),
):
    """Spawn an agent directly (without the server)."""
    try:
        backend_type = AgentBackendType(backend)
    except ValueError:
        console.print(f"[red]Invalid backend: {backend}[/]")
        raise typer.Exit(1)

    backend_impl = get_backend(backend_type)
    if not backend_impl.is_available():
        console.print(f"[red]Backend not available: {backend}[/]")
        console.print(f"[dim]Binary '{backend_impl.binary_name}' not found in PATH[/]")
        raise typer.Exit(1)

    config = AgentConfig(
        backend=backend_type,
        prompt=prompt,
        working_directory=working_dir,
        max_turns=max_turns,
        max_budget_usd=max_budget,
    )

    agent = AgentState(config=config, status=AgentStatus.STARTING)

    if not json_output:
        console.print(f"[bold]Spawning agent {agent.id}[/]")
        console.print(f"[dim]Backend: {backend}[/]")

    # Create process manager and spawn
    process_manager = ProcessManager()

    try:
        managed = process_manager.spawn(agent)
        agent.status = AgentStatus.RUNNING
        agent.pid = managed.process.pid

        if not json_output:
            console.print(f"[green]Agent started with PID {agent.pid}[/]")

        if follow:
            # Stream output
            for chunk in process_manager.iter_output(agent.id, timeout=1.0):
                if json_output:
                    print(chunk.model_dump_json())
                else:
                    if chunk.content:
                        console.print(chunk.content)
                    elif chunk.raw_line:
                        console.print(f"[dim]{chunk.raw_line.rstrip()}[/]")

        # Wait for completion
        exit_code = managed.process.wait()

        if json_output:
            result = {
                "agent_id": agent.id,
                "exit_code": exit_code,
                "status": "completed" if exit_code == 0 else "failed",
            }
            print(json.dumps(result))
        else:
            if exit_code == 0:
                console.print("[green]Agent completed successfully[/]")
            else:
                console.print(f"[red]Agent failed with exit code {exit_code}[/]")

        raise typer.Exit(exit_code)

    except KeyboardInterrupt:
        if not json_output:
            console.print("\n[yellow]Interrupted. Terminating agent...[/]")
        process_manager.terminate(agent.id, timeout=5.0)
        raise typer.Exit(130)

    finally:
        process_manager.cleanup(agent.id)


@app.command("list")
def list_agents(
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status"
    ),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """List agents from the persisted state."""
    agent_store = AgentStateStore(persist=True)
    agent_store.load_all()

    agents = agent_store.values()

    if status:
        try:
            status_enum = AgentStatus(status)
            agents = [a for a in agents if a.status == status_enum]
        except ValueError:
            console.print(f"[red]Invalid status: {status}[/]")
            raise typer.Exit(1)

    agents.sort(key=lambda a: a.created_at, reverse=True)

    if json_output:
        print(json.dumps([a.model_dump(mode="json") for a in agents], default=str))
        return

    if not agents:
        console.print("[dim]No agents found[/]")
        return

    table = Table(title="Agents")
    table.add_column("ID", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Backend")
    table.add_column("Created")
    table.add_column("Duration")

    for agent in agents:
        duration = ""
        if agent.duration_seconds() is not None:
            duration = f"{agent.duration_seconds():.1f}s"

        status_color = {
            AgentStatus.RUNNING: "green",
            AgentStatus.COMPLETED: "blue",
            AgentStatus.FAILED: "red",
            AgentStatus.TERMINATED: "yellow",
        }.get(agent.status, "white")

        table.add_row(
            agent.id[:8],
            f"[{status_color}]{agent.status.value}[/]",
            str(agent.config.backend),
            agent.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            duration,
        )

    console.print(table)


@app.command()
def logs(
    agent_id: str = typer.Argument(..., help="Agent ID (can be partial)"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    lines: int = typer.Option(100, "--lines", "-n", help="Number of lines to show"),
):
    """View agent logs."""
    from ..common import get_logs_dir

    logs_dir = get_logs_dir()

    # Find matching log file
    matching = list(logs_dir.glob(f"agent-{agent_id}*.log"))
    if not matching:
        # Try partial match
        matching = [f for f in logs_dir.glob("agent-*.log") if agent_id in f.name]

    if not matching:
        console.print(f"[red]No logs found for agent: {agent_id}[/]")
        raise typer.Exit(1)

    if len(matching) > 1:
        console.print("[yellow]Multiple matches found:[/]")
        for f in matching:
            console.print(f"  - {f.name}")
        console.print("[dim]Please provide a more specific agent ID[/]")
        raise typer.Exit(1)

    log_file = matching[0]

    if follow:
        # Tail -f style following
        console.print(f"[dim]Following {log_file.name}... (Ctrl+C to stop)[/]")
        try:
            with open(log_file) as f:
                # Go to end
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        console.print(line.rstrip())
                    else:
                        time.sleep(0.1)
        except KeyboardInterrupt:
            pass
    else:
        # Show last N lines
        with open(log_file) as f:
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                console.print(line.rstrip())


@app.command()
def backends():
    """List available agent backends."""
    available = get_available_backends()

    if not available:
        console.print("[red]No backends available[/]")
        raise typer.Exit(1)

    table = Table(title="Available Backends")
    table.add_column("Type", style="cyan")
    table.add_column("Binary")
    table.add_column("Path")
    table.add_column("Streaming")
    table.add_column("Resume")

    for backend in available:
        caps = backend.get_capabilities()
        table.add_row(
            str(backend.backend_type),
            backend.binary_name,
            str(backend.get_binary_path()),
            "[green]Yes[/]" if caps.streaming else "[red]No[/]",
            "[green]Yes[/]" if caps.resume else "[red]No[/]",
        )

    console.print(table)


@app.command()
def sessions(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """List sessions."""
    session_manager = SessionManager(persist=True)
    sessions = session_manager.list_sessions()

    if json_output:
        print(
            json.dumps(
                [s.metadata.model_dump(mode="json") for s in sessions], default=str
            )
        )
        return

    if not sessions:
        console.print("[dim]No sessions found[/]")
        return

    table = Table(title="Sessions")
    table.add_column("ID", style="cyan")
    table.add_column("Backend")
    table.add_column("Status", style="magenta")
    table.add_column("Turns")
    table.add_column("Updated")

    for session in sessions:
        table.add_row(
            session.metadata.id[:8],
            str(session.metadata.backend),
            session.status.value,
            str(session.metadata.total_turns),
            session.metadata.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

    console.print(table)


@app.command()
def terminate(
    agent_id: str = typer.Argument(..., help="Agent ID to terminate"),
    force: bool = typer.Option(False, "--force", "-f", help="Force kill"),
):
    """Terminate a running agent."""
    agent_store = AgentStateStore(persist=True)
    agent_store.load_all()

    # Find agent
    agent = agent_store.get(agent_id)
    if agent is None:
        # Try partial match
        for key in agent_store.keys():
            if key.startswith(agent_id):
                agent = agent_store.get(key)
                break

    if agent is None:
        console.print(f"[red]Agent not found: {agent_id}[/]")
        raise typer.Exit(1)

    if not agent.is_running():
        console.print(f"[yellow]Agent is not running (status: {agent.status})[/]")
        raise typer.Exit(0)

    process_manager = ProcessManager()

    try:
        if force:
            process_manager.kill(agent.id)
            console.print(f"[green]Agent {agent.id[:8]} killed[/]")
        else:
            process_manager.terminate(agent.id)
            console.print(f"[green]Agent {agent.id[:8]} terminated[/]")
    except Exception as e:
        console.print(f"[red]Failed to terminate agent: {e}[/]")
        raise typer.Exit(1)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

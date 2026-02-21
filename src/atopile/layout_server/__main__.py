"""CLI entry point: python -m atopile.layout_server <path.kicad_pcb> [--port 8100]."""

from __future__ import annotations

from pathlib import Path

import typer


def main(
    pcb_path: Path = typer.Argument(..., help="Path to .kicad_pcb file"),
    port: int = typer.Option(8100, help="Server port"),
    host: str = typer.Option("127.0.0.1", help="Server host"),
) -> None:
    if not pcb_path.is_file():
        raise typer.BadParameter(f"File not found: {pcb_path}", param_hint="pcb_path")

    from atopile.layout_server.server import create_app

    app = create_app(pcb_path)

    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    typer.run(main)

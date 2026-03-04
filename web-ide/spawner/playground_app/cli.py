from __future__ import annotations

import typer
import uvicorn

from playground_app.config import DEFAULT_CONFIG_PATH, load_config
from playground_app.fly_token import FlyTokenError, resolve_fly_api_token
from playground_app.frontend import build_frontend
from playground_app.infra.deploy import deploy as deploy_infra
from playground_app.infra.status import status as infra_status_run
from playground_app.server.app import create_app

app = typer.Typer(no_args_is_help=True)
server_app = typer.Typer(no_args_is_help=True)
infra_app = typer.Typer(no_args_is_help=True)
web_app = typer.Typer(no_args_is_help=True, hidden=True)


@server_app.command("start")
def server_start() -> None:
    cfg = load_config(DEFAULT_CONFIG_PATH)
    try:
        fly_token = resolve_fly_api_token()
    except FlyTokenError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    if cfg.server.auto_build_frontend:
        build_frontend()

    uvicorn.run(
        create_app(cfg, fly_token=fly_token),
        host=cfg.server.host,
        port=cfg.server.port,
    )


@infra_app.command("deploy")
def infra_deploy() -> None:
    cfg = load_config(DEFAULT_CONFIG_PATH)
    try:
        deploy_infra(cfg)
    except Exception as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


@infra_app.command("status")
def infra_status(
    local: bool = typer.Option(
        False,
        "--local",
        help="Read health from local spawner at http://127.0.0.1:<server.port>/api/health",
    ),
) -> None:
    cfg = load_config(DEFAULT_CONFIG_PATH)
    try:
        infra_status_run(cfg, local=local)
    except Exception as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


@web_app.command("build")
def web_build() -> None:
    build_frontend(force=True)


app.add_typer(server_app, name="server")
app.add_typer(infra_app, name="infra")
app.add_typer(web_app, name="web")

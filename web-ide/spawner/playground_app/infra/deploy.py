from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from playground_app.config import AppConfig


def _run(
    cmd: list[str],
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=False,
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        details: list[str] = []
        if result.stdout.strip():
            details.append(f"stdout:\n{result.stdout.strip()}")
        if result.stderr.strip():
            details.append(f"stderr:\n{result.stderr.strip()}")
        if not details:
            details.append("no subprocess output")
        formatted_cmd = " ".join(shlex.quote(part) for part in cmd)
        raise RuntimeError(f"Command failed with exit {result.returncode}: {formatted_cmd}\n\n" + "\n\n".join(details))
    return result


def _resolve_fly() -> str:
    for candidate in ("fly", "flyctl"):
        if shutil.which(candidate):
            return candidate
    raise RuntimeError("flyctl not found. Install flyctl and ensure it is in PATH.")


def _token_can_access_ws(
    token: str,
    *,
    ws_app: str,
    machines_api: str,
) -> bool:
    token = token.strip()
    if not token:
        return False
    endpoint = f"{machines_api.rstrip('/')}/v1/apps/{ws_app}/machines"
    request = urllib.request.Request(
        endpoint,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status == 200
    except urllib.error.HTTPError:
        return False
    except urllib.error.URLError:
        return False


def _create_ws_deploy_token(fly: str, ws_app: str) -> str:
    result = _run(
        [
            fly,
            "tokens",
            "create",
            "deploy",
            "--app",
            ws_app,
            "--name",
            "atopile playground runtime",
            "--json",
        ],
        check=False,
    )
    if result.returncode != 0:
        return ""
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ""
    token = payload.get("token")
    if not isinstance(token, str):
        return ""
    return token.strip()


def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    result = subprocess.run(
        ["docker", "info"],
        check=False,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _playground_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _derive_versions() -> tuple[str, str]:
    repo = _repo_root()
    version = "0.0.0dev"
    semver = "0.0.0-dev0"
    try:
        result = _run(["uv", "run", "ato", "--version"], cwd=repo)
        version = result.stdout.strip() or version
    except Exception:
        pass
    try:
        result = _run(["uv", "run", "ato", "--semver"], cwd=repo)
        semver = result.stdout.strip() or semver
    except Exception:
        pass
    return version, semver


def _apps_list(fly: str) -> list[str]:
    out = _run([fly, "apps", "list", "--json"]).stdout
    data = json.loads(out)
    names: list[str] = []
    for entry in data:
        name = entry.get("Name") or entry.get("name")
        if isinstance(name, str):
            names.append(name)
    return names


def _machines_list(fly: str, app: str) -> list[dict]:
    out = _run([fly, "machines", "list", "--app", app, "--json"]).stdout
    data = json.loads(out)
    return data if isinstance(data, list) else []


def _destroy_all_machines(fly: str, app: str) -> None:
    for machine in _machines_list(fly, app):
        machine_id = machine.get("id")
        if machine_id:
            _run(
                [fly, "machines", "destroy", machine_id, "--app", app, "--force"],
                check=False,
            )


def _render_spawner_manifest(cfg: AppConfig) -> str:
    spawner = cfg.infra.spawner
    service = spawner.http_service
    vm = spawner.vm
    return f"""app = '{spawner.app}'
primary_region = '{spawner.primary_region}'

[build]
  dockerfile = '{spawner.dockerfile}'

[http_service]
  internal_port = {service.internal_port}
  force_https = {str(service.force_https).lower()}
  auto_stop_machines = '{service.auto_stop_machines}'
  auto_start_machines = {str(service.auto_start_machines).lower()}
  min_machines_running = {service.min_machines_running}

[[vm]]
  cpu_kind = '{vm.cpu_kind}'
  cpus = {vm.cpus}
  memory_mb = {vm.memory_mb}
"""


def _render_ws_manifest(cfg: AppConfig) -> str:
    ws = cfg.infra.ws
    return f"""app = '{ws.app}'
primary_region = '{ws.region}'

[build]
  dockerfile = '{ws.dockerfile}'
"""


def _resolve_runtime_fly_token(fly: str, cfg: AppConfig) -> str:
    # Prefer explicit env override only if it can actually access the workspace machines API.
    env_token = os.environ.get("FLY_API_TOKEN", "").strip()
    if env_token and _token_can_access_ws(
        env_token,
        ws_app=cfg.infra.ws.app,
        machines_api=cfg.infra.ws.machines_api,
    ):
        return env_token
    if env_token:
        print(
            "Warning: FLY_API_TOKEN is set but cannot access workspace machines API; "
            "falling back to flyctl-generated token."
        )

    deploy_token = _create_ws_deploy_token(fly, cfg.infra.ws.app)
    if deploy_token and _token_can_access_ws(
        deploy_token,
        ws_app=cfg.infra.ws.app,
        machines_api=cfg.infra.ws.machines_api,
    ):
        return deploy_token
    if deploy_token:
        print("Warning: deploy token created by flyctl cannot access workspace machines API.")

    auth_result = _run([fly, "auth", "token"], check=False)
    auth_token = auth_result.stdout.strip() if auth_result.returncode == 0 else ""
    if auth_token and _token_can_access_ws(
        auth_token,
        ws_app=cfg.infra.ws.app,
        machines_api=cfg.infra.ws.machines_api,
    ):
        return auth_token
    if auth_token:
        print("Warning: token from `fly auth token` cannot access workspace machines API.")

    raise RuntimeError(
        "Could not resolve a usable Fly API token. "
        "Set FLY_API_TOKEN with access to workspace app machines or run `fly auth login`."
    )


def deploy(cfg: AppConfig) -> None:
    fly = _resolve_fly()
    _run([fly, "auth", "whoami"])
    runtime_fly_token = _resolve_runtime_fly_token(fly, cfg)

    apps = set(_apps_list(fly))
    for app_name in (cfg.infra.ws.app, cfg.infra.spawner.app):
        if app_name not in apps:
            _run([fly, "apps", "create", app_name])

    version, semver = _derive_versions()
    repo_root = _repo_root()
    source_hash = _run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root)
    source_hash_value = source_hash.stdout.strip()

    playground_root = _playground_root()
    temp_ws_manifest_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            prefix="fly.ws.generated.",
            suffix=".toml",
            dir=playground_root,
            delete=False,
            encoding="utf-8",
        ) as ws_manifest:
            ws_manifest.write(_render_ws_manifest(cfg))
            temp_ws_manifest_path = Path(ws_manifest.name)

        use_local_builder = _docker_available()
        ws_deploy_cmd = [
            fly,
            "deploy",
            "--config",
            str(temp_ws_manifest_path),
            "--build-arg",
            f"SOURCE_HASH={source_hash_value}",
            "--build-arg",
            f"ATOPILE_VERSION={version}",
            "--build-arg",
            f"ATOPILE_SEMVER={semver}",
            "--image-label",
            cfg.infra.ws.image_label,
            "--strategy",
            cfg.infra.ws.deploy_strategy,
            f"--ha={str(cfg.infra.ws.deploy_ha).lower()}",
        ]
        ws_deploy_cmd.append("--local-only" if use_local_builder else "--remote-only")
        if not use_local_builder:
            print("Docker unavailable; deploying workspace image with Fly remote builder.")
        _run(ws_deploy_cmd, cwd=repo_root)
    finally:
        if temp_ws_manifest_path and temp_ws_manifest_path.exists():
            temp_ws_manifest_path.unlink()

    _destroy_all_machines(fly, cfg.infra.ws.app)

    _run(
        [
            fly,
            "secrets",
            "set",
            "--app",
            cfg.infra.spawner.app,
            f"FLY_API_TOKEN={runtime_fly_token}",
        ]
    )

    temp_manifest_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            prefix="fly.spawner.generated.",
            suffix=".toml",
            dir=playground_root,
            delete=False,
            encoding="utf-8",
        ) as temp_file:
            temp_file.write(_render_spawner_manifest(cfg))
            temp_manifest_path = Path(temp_file.name)

        _run([fly, "deploy", "--config", temp_manifest_path.name], cwd=playground_root)
    finally:
        if temp_manifest_path and temp_manifest_path.exists():
            temp_manifest_path.unlink()

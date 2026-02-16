#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import tomllib


@dataclass(frozen=True)
class PipelineConfig:
    repo_root: Path
    cache_dir: Path
    source_sqlite: Path
    mode: str
    snapshot_name: str
    max_components: int
    stage1_where: str
    stage1_chunk_size: int
    stage1_workers: int
    stage1_retry_attempts: int
    stage1_retry_backoff_s: float
    stage1_sleep_s: float
    stage1_log_path: Path
    stage2_keep_snapshots: int
    stage2_allow_partial: bool
    serve_host: str
    serve_port: int


def _utc_snapshot_name() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _required_str(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid config value: {key}")
    return value.strip()


def load_config(config_path: Path) -> PipelineConfig:
    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    paths = payload.get("paths", {})
    workflow = payload.get("workflow", {})
    stage1 = payload.get("stage1", {})
    stage2 = payload.get("stage2", {})
    serve = payload.get("serve", {})

    repo_root = Path(_required_str(paths, "repo_root"))
    snapshot_name = str(workflow.get("snapshot_name", "auto")).strip() or "auto"
    if snapshot_name == "auto":
        snapshot_name = _utc_snapshot_name()

    return PipelineConfig(
        repo_root=repo_root,
        cache_dir=Path(_required_str(paths, "cache_dir")),
        source_sqlite=Path(_required_str(paths, "source_sqlite")),
        mode=str(workflow.get("mode", "all-in-one-once")),
        snapshot_name=snapshot_name,
        max_components=int(workflow.get("max_components", 0)),
        stage1_where=str(stage1.get("where", "stock > 0")),
        stage1_chunk_size=int(stage1.get("chunk_size", 50000)),
        stage1_workers=int(stage1.get("workers", 32)),
        stage1_retry_attempts=int(stage1.get("retry_attempts", 3)),
        stage1_retry_backoff_s=float(stage1.get("retry_backoff_s", 2.0)),
        stage1_sleep_s=float(stage1.get("sleep_s", 0.0)),
        stage1_log_path=Path(str(stage1.get("log_path", "/tmp/stage1_fetch_all.log"))),
        stage2_keep_snapshots=int(stage2.get("keep_snapshots", 2)),
        stage2_allow_partial=bool(stage2.get("allow_partial", False)),
        serve_host=str(serve.get("host", "127.0.0.1")),
        serve_port=int(serve.get("port", 8079)),
    )


def _base_env(cfg: PipelineConfig) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(cfg.repo_root / "src")
    env["ATOPILE_COMPONENTS_CACHE_DIR"] = str(cfg.cache_dir)
    env["ATOPILE_COMPONENTS_SOURCE_SQLITE"] = str(cfg.source_sqlite)
    env["ATOPILE_COMPONENTS_SNAPSHOT_NAME"] = cfg.snapshot_name
    env["ATOPILE_COMPONENTS_KEEP_SNAPSHOTS"] = str(cfg.stage2_keep_snapshots)
    env["ATOPILE_COMPONENTS_ALLOW_PARTIAL"] = "1" if cfg.stage2_allow_partial else "0"
    env["ATOPILE_COMPONENTS_SERVE_HOST"] = cfg.serve_host
    env["ATOPILE_COMPONENTS_SERVE_PORT"] = str(cfg.serve_port)
    env["SOURCE_SQLITE"] = str(cfg.source_sqlite)
    env["ATOPILE_COMPONENTS_CHUNK_SIZE"] = str(cfg.stage1_chunk_size)
    env["ATOPILE_COMPONENTS_ROUNDTRIP_WORKERS"] = str(cfg.stage1_workers)
    env["ATOPILE_COMPONENTS_ROUNDTRIP_RETRY_ATTEMPTS"] = str(cfg.stage1_retry_attempts)
    env["ATOPILE_COMPONENTS_ROUNDTRIP_RETRY_BACKOFF_S"] = str(cfg.stage1_retry_backoff_s)
    env["ATOPILE_COMPONENTS_WHERE"] = cfg.stage1_where
    env["ATOPILE_COMPONENTS_LOG_PATH"] = str(cfg.stage1_log_path)
    return env


def _cmds_for_mode(cfg: PipelineConfig) -> list[list[str]]:
    py = str(cfg.repo_root / ".venv" / "bin" / "python")
    sh = str(cfg.repo_root / "scripts" / "run_stage1_fetch_all.sh")
    cmds: list[list[str]] = []

    def stage1_all() -> list[str]:
        return [sh]

    def stage2_build() -> list[str]:
        cmd = [
            py,
            "-m",
            "backend.components.transform.build_snapshot",
            "--source-sqlite",
            str(cfg.source_sqlite),
            "--snapshot-name",
            cfg.snapshot_name,
        ]
        if cfg.max_components > 0:
            cmd.extend(["--max-components", str(cfg.max_components)])
        return cmd

    def stage2_publish() -> list[str]:
        cmd = [
            py,
            "-m",
            "backend.components.transform.publish_snapshot",
            cfg.snapshot_name,
            "--keep-snapshots",
            str(cfg.stage2_keep_snapshots),
        ]
        if cfg.stage2_allow_partial:
            cmd.append("--allow-partial")
        return cmd

    def serve() -> list[str]:
        return [py, "-m", "backend.components.serve.main"]

    mode = cfg.mode
    if mode == "stage1-all":
        cmds.append(stage1_all())
    elif mode == "stage2-build":
        cmds.append(stage2_build())
    elif mode == "stage2-publish":
        cmds.append(stage2_publish())
    elif mode == "processor-once":
        cmds.extend([stage2_build(), stage2_publish()])
    elif mode == "serve":
        cmds.append(serve())
    elif mode == "all-in-one-once":
        cmds.extend([stage1_all(), stage2_build(), stage2_publish()])
    else:
        raise ValueError(
            "workflow.mode must be one of: "
            "stage1-all, stage2-build, stage2-publish, processor-once, serve, all-in-one-once"
        )
    return cmds


def _print_plan(cfg: PipelineConfig, cmds: list[list[str]]) -> None:
    print(f"mode={cfg.mode}")
    print(f"repo_root={cfg.repo_root}")
    print(f"cache_dir={cfg.cache_dir}")
    print(f"source_sqlite={cfg.source_sqlite}")
    print(f"snapshot_name={cfg.snapshot_name}")
    print(f"max_components={cfg.max_components}")
    print("commands:")
    for idx, cmd in enumerate(cmds, start=1):
        joined = " ".join(subprocess.list2cmdline([part]) for part in cmd)
        print(f"  {idx}. {joined}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Declarative stage1/stage2(/serve) pipeline runner from a single TOML file."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("components-pipeline.toml"),
        help="Path to pipeline TOML config.",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--plan", action="store_true", help="Print resolved plan only.")
    mode_group.add_argument("--apply", action="store_true", help="Execute resolved plan.")
    args = parser.parse_args(argv)

    cfg = load_config(args.config.resolve())
    cmds = _cmds_for_mode(cfg)
    _print_plan(cfg, cmds)
    if not args.apply:
        return 0

    env = _base_env(cfg)
    for cmd in cmds:
        print(f"running: {' '.join(cmd)}")
        subprocess.run(cmd, cwd=cfg.repo_root, env=env, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

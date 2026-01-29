"""CLI command definition for `ato build`."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import typer
from typing_extensions import Annotated

from atopile.buildutil import generate_build_id, generate_build_timestamp
from atopile.dataclasses import (
    Build,
    BuildStatus,
)
from atopile.logging import get_logger
from atopile.logging_utils import BuildPrinter, print_subprocess_output
from atopile.model.build_queue import BuildQueue
from atopile.telemetry import capture

logger = get_logger(__name__)

# Constants
DEFAULT_WORKER_COUNT = os.cpu_count() or 4


def discover_projects(root: Path) -> list[Path]:
    """
    Discover ato projects in a directory.

    If root contains ato.yaml, returns [root].
    Otherwise, finds all directories containing ato.yaml below root.
    """
    config_file = root / "ato.yaml"
    if config_file.exists():
        return [root]

    # Find all ato.yaml files below root (non-recursive in .ato/modules)
    projects = []
    for path in root.rglob("ato.yaml"):
        # Skip .ato/modules (dependencies)
        if ".ato" in path.parts:
            continue
        projects.append(path.parent)

    return sorted(projects)




def _run_build_queue(
    builds: list[Build],
    *,
    jobs: int,
    verbose: bool,
) -> dict[str, int]:
    """Run builds through a local BuildQueue and return build_id -> exit code."""
    from atopile.model.sqlite import BuildHistory

    if not builds:
        return {}

    # Initialize database
    BuildHistory.init_db()

    # Verbose mode runs sequentially (one build at a time)
    max_concurrent = 1 if verbose else jobs
    queue = BuildQueue(max_concurrent=max_concurrent)

    build_ids = [build.build_id for build in builds if build.build_id]
    display_names = {
        build.build_id: build.display_name for build in builds if build.build_id
    }

    for build in builds:
        queue.enqueue(build)

    started: set[str] = set()
    reported: set[str] = set()

    TERMINAL_STATUSES = (
        BuildStatus.SUCCESS,
        BuildStatus.WARNING,
        BuildStatus.FAILED,
        BuildStatus.CANCELLED,
    )

    with BuildPrinter(verbose=verbose) as printer:

        # For verbose mode, stream subprocess output to console
        if verbose:
            # Buffer output until the build header is printed to keep ordering.
            pending_output: dict[str, list[tuple[str, bool]]] = {}

            def _flush_pending(build_id: str) -> None:
                buffered = pending_output.pop(build_id, [])
                for text, is_stderr in buffered:
                    print_subprocess_output(text, is_stderr)

            def on_output(build_id: str, text: str, is_stderr: bool) -> None:
                if build_id not in started:
                    pending_output.setdefault(build_id, []).append((text, is_stderr))
                    return
                print_subprocess_output(text, is_stderr)

            queue.on_output = on_output

        def on_update() -> None:
            for build_id in build_ids:
                build = queue.find_build(build_id)
                if not build:
                    continue

                display_name = display_names.get(build_id, build.display_name)

                # Build started
                if (
                    build.status in (BuildStatus.BUILDING, *TERMINAL_STATUSES)
                    and build_id not in started
                ):
                    printer.build_started(build_id, display_name, total=build.total_stages)
                    started.add(build_id)
                    if verbose:
                        _flush_pending(build_id)

                # Stage updates
                if build.stages:
                    printer.stage_update(build_id, build.stages, build.total_stages)

                # Build completed
                if build.status in TERMINAL_STATUSES and build_id not in reported:
                    printer.build_completed(
                        build_id,
                        build.status,
                        warnings=build.warnings,
                        errors=build.errors,
                    )
                    reported.add(build_id)

        results = queue.wait_for_builds(build_ids, on_update=on_update, poll_interval=0.1)

        # Print build summary boxes after all builds complete
        completed_builds = [
            queue.find_build(build_id)
            for build_id in build_ids
            if queue.find_build(build_id)
        ]
        printer.print_summary(completed_builds)

        return results


def _run_single_build() -> None:
    """
    Run a single build target (worker mode).

    This is called when ATO_BUILD_WORKER is set by the parent process.
    Stages are written to the build history DB as they complete.
    """
    import sys

    from atopile import buildutil
    from atopile.buildutil import BuildStepContext
    from atopile.config import config
    from atopile.errors import UserException, iter_leaf_exceptions
    from atopile.model.sqlite import BuildHistory

    # Get the single build target from config
    build_names = list(config.selected_builds)
    if len(build_names) != 1:
        raise RuntimeError(
            f"Worker mode expects exactly 1 build, got {len(build_names)}"
        )

    build_name = build_names[0]

    # Read build_id from environment (passed by parent process)
    build_id = os.environ.get("ATO_BUILD_ID")

    # Initialize build history DB so the worker can write stages
    BuildHistory.init_db()

    # Create build context to track completed stages
    ctx = BuildStepContext(build=None, build_id=build_id)

    try:
        with config.select_build(build_name):
            buildutil.build(ctx=ctx)
    except Exception as exc:
        for e in iter_leaf_exceptions(exc):
            logger.error(e, exc_info=e)
        sys.exit(1)

    # Note: BuildLogger.close_all() is registered as an atexit handler,
    # so logs will be flushed during process shutdown.


def _build_all_projects(
    root: Path,
    jobs: int,
    frozen: bool | None = None,
    selected_builds: list[str] | None = None,
    verbose: bool = False,
    targets: list[str] | None = None,
    exclude_targets: list[str] | None = None,
    keep_picked_parts: bool | None = None,
    keep_net_names: bool | None = None,
    keep_designators: bool | None = None,
) -> None:
    """
    Build all projects in a directory.

    Discovers all ato.yaml files and builds all their targets.
    Use -b to filter to specific build targets across all projects.
    """
    from atopile.config import ProjectConfig

    # Discover projects
    projects = discover_projects(root)

    if not projects:
        logger.error("No ato projects found in %s", root)
        raise typer.Exit(1)

    logger.info("Found %d projects", len(projects))

    # Collect build tasks from all projects
    # Format: (build_name, project_root, project_name)
    build_tasks: list[tuple[str, Path, str | None]] = []

    for project_path in projects:
        project_name = project_path.name

        # Load project config to get build targets
        project_config = ProjectConfig.from_path(project_path)
        if project_config is None:
            logger.warning("Skipping %s: could not load config", project_name)
            continue

        # Get builds to run for this project
        if selected_builds:
            # Use specified builds if they exist in this project
            builds = [b for b in selected_builds if b in project_config.builds]
        else:
            # Build ALL targets in the project
            builds = list(project_config.builds.keys())

        if not builds:
            logger.warning("Skipping %s: no matching builds", project_name)
            continue

        for build_name in builds:
            build_tasks.append((build_name, project_path, project_name))

    if not build_tasks:
        logger.error("No builds to run")
        raise typer.Exit(1)

    logger.info(
        "Building %d targets across %d projects (max %d concurrent)",
        len(build_tasks),
        len(projects),
        jobs,
    )

    # Initialize build history database
    timestamp = generate_build_timestamp()
    builds: list[Build] = []
    for build_name, project_root, project_name in build_tasks:
        project_path = str(project_root.resolve())
        build_id = generate_build_id(project_path, build_name, timestamp)
        builds.append(
            Build(
                build_id=build_id,
                name=build_name,
                display_name=f"{project_name}/{build_name}" if project_name else build_name,
                project_root=project_path,
                project_name=project_name,
                target=build_name,
                timestamp=timestamp,
                frozen=frozen,
                status=BuildStatus.QUEUED,
                started_at=time.time(),
                include_targets=targets or [],
                exclude_targets=exclude_targets or [],
                keep_picked_parts=keep_picked_parts,
                keep_net_names=keep_net_names,
                keep_designators=keep_designators,
                verbose=verbose,
            )
        )

    results = _run_build_queue(builds, jobs=jobs, verbose=verbose)

    build_by_id = {build.build_id: build for build in builds if build.build_id}
    failed = [
        build_by_id[build_id].display_name
        for build_id, code in results.items()
        if code != 0 and build_id in build_by_id
    ]
    exit_code = _report_build_results(
        failed=failed,
        total=len(build_tasks),
        failed_names=failed[:10],
    )
    if exit_code != 0:
        raise typer.Exit(exit_code)


@capture("cli:build_start", "cli:build_end")
def build(
    entry: Annotated[
        str | None,
        typer.Argument(
            help="Path to the project directory or build target address "
            '("path_to.ato:Module")'
        ),
    ] = None,
    selected_builds: Annotated[
        list[str], typer.Option("--build", "-b", envvar="ATO_BUILD")
    ] = [],
    target: Annotated[
        list[str], typer.Option("--target", "-t", envvar="ATO_TARGET")
    ] = [],
    exclude_target: Annotated[
        list[str], typer.Option("--exclude-target", "-x", envvar="ATO_EXCLUDE_TARGET")
    ] = [],
    frozen: Annotated[
        bool | None,
        typer.Option(
            help="PCB must be rebuilt without changes. Useful in CI",
            envvar="ATO_FROZEN",
        ),
    ] = None,
    keep_picked_parts: Annotated[
        bool | None,
        typer.Option(
            help="Keep previously picked parts from PCB",
            envvar="ATO_KEEP_PICKED_PARTS",
        ),
    ] = None,
    keep_net_names: Annotated[
        bool | None,
        typer.Option(
            help="Keep net names from PCB",
            envvar="ATO_KEEP_NET_NAMES",
        ),
    ] = None,
    keep_designators: Annotated[
        bool | None,
        typer.Option(
            help="Keep designators from PCB",
            envvar="ATO_KEEP_DESIGNATORS",
        ),
    ] = None,
    standalone: bool = False,
    open_layout: Annotated[
        bool | None, typer.Option("--open", envvar="ATO_OPEN_LAYOUT")
    ] = None,
    all_projects: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Build all projects in directory (recursively finds ato.yaml)",
        ),
    ] = False,
    jobs: Annotated[
        int,
        typer.Option(
            "--jobs",
            "-j",
            help=f"Max concurrent builds (default: {DEFAULT_WORKER_COUNT})",
        ),
    ] = DEFAULT_WORKER_COUNT,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Run sequentially without live display",
        ),
    ] = False,
):
    """
    Build the specified --target(s) or the targets specified by the build config.
    Optionally specify a different entrypoint with the argument ENTRY.

    Use --all to build all projects in a directory (e.g., `ato build --all`).

    eg. `ato build --target my_target path/to/source.ato:module.path`
    """
    from atopile.config import config
    from faebryk.libs.app.pcb import open_pcb
    from faebryk.libs.kicad.ipc import reload_pcb
    from faebryk.libs.project.dependencies import ProjectDependencies

    # Check for verbose mode from CLI flag or environment variable (for workers)
    if verbose or os.environ.get("ATO_VERBOSE") == "1":
        logging.getLogger().setLevel(logging.DEBUG)

    # Enable faulthandler for crash debugging in workers
    if os.environ.get("ATO_SAFE"):
        import faulthandler

        faulthandler.enable()

    # Worker mode - run single build directly (no config needed yet)
    if os.environ.get("ATO_BUILD_WORKER"):
        config.apply_options(
            entry=entry,
            selected_builds=selected_builds,
            include_targets=target,
            exclude_targets=exclude_target,
            standalone=standalone,
            frozen=frozen,
            keep_picked_parts=keep_picked_parts,
            keep_net_names=keep_net_names,
            keep_designators=keep_designators,
        )

        # Install dependencies if needed (same as single project mode)
        deps = ProjectDependencies(sync_versions=False)
        if deps.not_installed_dependencies:
            logger.info("Installing missing dependencies")
            for dep in deps.not_installed_dependencies:
                try:  # protect against parallel worker race condition
                    assert dep.dist is not None
                    from faebryk.libs.project.dependencies import _log_add_package

                    _log_add_package(dep.identifier, dep.dist.version)
                    dep.dist.install(dep.target_path)
                except FileExistsError:
                    logger.debug(
                        f"Dependency {dep.identifier} already exists at "
                        f"{dep.target_path}"
                    )

        _run_single_build()
        return

    # Multi-project mode: discover and build all projects
    if all_projects:
        _build_all_projects(
            root=Path.cwd(),
            jobs=jobs,
            frozen=frozen,
            selected_builds=selected_builds,
            verbose=verbose,
            targets=target,
            exclude_targets=exclude_target,
            keep_picked_parts=keep_picked_parts,
            keep_net_names=keep_net_names,
            keep_designators=keep_designators,
        )
        return

    # Single project mode
    config.apply_options(
        entry=entry,
        selected_builds=selected_builds,
        include_targets=target,
        exclude_targets=exclude_target,
        standalone=standalone,
        frozen=frozen,
        keep_picked_parts=keep_picked_parts,
        keep_net_names=keep_net_names,
        keep_designators=keep_designators,
    )

    deps = ProjectDependencies(sync_versions=False)
    if deps.not_installed_dependencies:
        logger.info("Installing missing dependencies")
        deps.install_missing_dependencies()

    if open_layout is not None:
        config.project.open_layout_on_build = open_layout

    # Get the list of builds to run
    build_names = list(config.selected_builds)
    project_root = config.project.paths.root

    timestamp = generate_build_timestamp()
    builds: list[Build] = []
    for build_name in build_names:
        build_id = generate_build_id(str(project_root.resolve()), build_name, timestamp)
        builds.append(
            Build(
                build_id=build_id,
                name=build_name,
                display_name=build_name,
                project_root=str(project_root.resolve()),
                target=build_name,
                entry=entry,
                standalone=standalone,
                timestamp=timestamp,
                frozen=frozen,
                status=BuildStatus.QUEUED,
                started_at=time.time(),
                include_targets=target,
                exclude_targets=exclude_target,
                keep_picked_parts=keep_picked_parts,
                keep_net_names=keep_net_names,
                keep_designators=keep_designators,
                verbose=verbose,
            )
        )

    results = _run_build_queue(builds, jobs=jobs, verbose=verbose)

    from atopile.logging import BuildLogger

    BuildLogger.close_all()

    build_by_id = {build.build_id: build for build in builds if build.build_id}
    failed = [
        build_by_id[build_id].display_name
        for build_id, code in results.items()
        if code != 0 and build_id in build_by_id
    ]

    build_exit_code = _report_build_results(
        failed=failed,
        total=len(build_names),
        failed_names=failed,
    )

    # Open layouts if requested
    for build_name in build_names:
        build_cfg = config.project.builds[build_name]

        opened = False
        if config.should_open_layout_on_build():
            try:
                open_pcb(build_cfg.paths.layout)
                opened = True
            except FileNotFoundError:
                continue
            except RuntimeError:
                pass

        if not opened:
            try:
                reload_pcb(
                    build_cfg.paths.layout, backup_path=build_cfg.paths.output_base
                )
            except Exception as e:
                logger.warning(f"{e}\nReload pcb manually in KiCAD")

    if build_exit_code != 0:
        raise typer.Exit(build_exit_code)


def _report_build_results(
    *,
    failed: list[str],
    total: int,
    failed_names: list[str] | None = None,
) -> int:
    """Report build results and return exit code (0 for success, 1 for failure)."""
    if failed:
        from atopile.errors import log_discord_banner

        log_discord_banner()
        logger.error("Build failed! %d of %d targets failed", len(failed), total)
        if failed_names:
            for name in failed_names:
                logger.error("  - %s", name)
        remaining = len(failed) - (len(failed_names) if failed_names else 0)
        if remaining > 0:
            logger.error("  ... and %d more", remaining)
        return 1

    if total > 1:
        logger.info("Build successful! 🚀 (%d targets)", total)
    else:
        logger.info("Build successful! 🚀")
    return 0

import contextlib
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.config import BuildType, config
from atopile.dataclasses import BuildStage
from atopile.errors import UserToolNotAvailableError, accumulate
from atopile.logging import get_logger
from faebryk.core.solver.solver import Solver
from faebryk.libs.util import once

if TYPE_CHECKING:
    from atopile.compiler.build import BuildFileResult, Linker

logger = get_logger(__name__)


def generate_build_id(project_path: str, target: str, timestamp: str) -> str:
    """
    Generate a unique build ID from project, target, and timestamp.

    This is the single source of truth for build ID generation.
    All components (server, CLI, logging) must use this function.

    Args:
        project_path: Absolute path to the project root
        target: Build target name
        timestamp: Timestamp string in format "%Y-%m-%d_%H-%M-%S"

    Returns:
        16-character hex string (truncated SHA256 hash)
    """
    content = f"{project_path}:{target}:{timestamp}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def generate_build_timestamp() -> str:
    """Generate a build timestamp in the standard format."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


@dataclass
class BuildContext:
    g: graph.GraphView
    tg: fbrk.TypeGraph
    build_type: BuildType
    app_type: graph.BoundNode | None = None
    app_class: type[fabll.Node] | None = None
    linker: "Linker | None" = None
    result: "BuildFileResult | None" = None
    app: fabll.Node | None = None


@dataclass
class BuildStepContext:
    build: BuildContext | None
    app: fabll.Node | None = None
    solver: Solver | None = None
    pcb: F.PCB | None = None
    stage: str | None = None
    build_id: str | None = None  # Build ID from server (via ATO_BUILD_ID env var)
    completed_stages: list[BuildStage] = field(default_factory=list)
    _stage_start_time: float = field(default=0.0, repr=False)

    def require_build(self) -> BuildContext:
        if self.build is None:
            raise RuntimeError("Build context is not initialized")
        return self.build

    def require_app(self) -> fabll.Node:
        if self.app is not None:
            return self.app
        if self.build is not None and self.build.app is not None:
            return self.build.app
        raise RuntimeError("App is not instantiated")

    def require_solver(self) -> Solver:
        if self.solver is None:
            raise RuntimeError("Solver is not initialized")
        return self.solver

    def require_pcb(self) -> F.PCB:
        if self.pcb is None:
            raise RuntimeError("PCB is not initialized")
        return self.pcb


@once
def _check_kicad_cli() -> bool:
    with contextlib.suppress(Exception):
        from kicadcliwrapper.generated.kicad_cli import kicad_cli

        kicad_cli(kicad_cli.version()).exec()
        return True

    return False


def run_build_targets(ctx: BuildStepContext) -> None:
    """Run build targets in dependency order."""
    import os

    from atopile import build_steps

    targets = {build_steps.generate_default.name} | set(config.build.targets) - set(
        config.build.exclude_targets
    )

    # Count targets from DAG without materializing the generator
    # (the generator yields based on succeeded status which we can't check upfront)
    subgraph = build_steps.muster.dependency_dag.get_subgraph(
        selector_func=lambda name: name in targets
        or any(
            alias in targets
            for alias in build_steps.muster.targets.get(name, build_steps.MusterTarget(name="", aliases=[], func=lambda _: None)).aliases
        )
    )
    all_target_names = set(subgraph.topologically_sorted())

    # Count non-virtual targets that will actually run
    total_stages = 0
    for name in all_target_names:
        target = build_steps.muster.targets.get(name)
        if not target or target.virtual:
            continue
        if target.name in config.build.exclude_targets:
            continue
        if build_steps.Tags.REQUIRES_KICAD in target.tags and not _check_kicad_cli():
            if target.implicit:
                continue
        total_stages += 1

    # Write total stage count to database so parent can show accurate progress
    build_id = os.environ.get("ATO_BUILD_ID") or ctx.build_id
    if build_id:
        from atopile.dataclasses import Build, BuildStatus
        from atopile.model.sqlite import BuildHistory

        # Just update total_stages - set() will merge with existing record
        BuildHistory.set(
            Build(
                build_id=build_id,
                name=config.build.name,
                display_name=config.build.name,
                status=BuildStatus.BUILDING,
                total_stages=total_stages,
            )
        )

    # Iterate generator properly - it yields targets only when their deps have succeeded
    with accumulate() as accumulator:
        for target in build_steps.muster.select(targets):
            if (
                build_steps.Tags.REQUIRES_KICAD in target.tags
                and not _check_kicad_cli()
            ):
                raise UserToolNotAvailableError("kicad-cli not found")

            with accumulator.collect():
                target(ctx)


def _load_python_app_class() -> type[fabll.Node]:
    """Initialize a specific .py build."""
    from atopile import errors
    from atopile.compiler.build import (
        FabllTypeFileNotFoundError,
        FabllTypeNotATypeError,
        FabllTypeNotNodeSubclassError,
        FabllTypeSymbolNotFoundError,
        import_fabll_type,
    )

    try:
        return import_fabll_type(
            config.build.entry_file_path, config.build.entry_section
        )
    except FabllTypeFileNotFoundError as e:
        raise errors.UserFileNotFoundError(
            f"Cannot find build entry {config.build.address}"
        ) from e
    except FabllTypeSymbolNotFoundError as e:
        raise errors.UserPythonModuleError(
            f"Cannot import build entry {config.build.address}"
        ) from e
    except FabllTypeNotATypeError as e:
        raise errors.UserPythonLoadError(
            f"Build entry {config.build.address} is not a module we can instantiate"
        ) from e
    except FabllTypeNotNodeSubclassError as e:
        raise errors.UserPythonConstructionError(
            f"Build entry {config.build.address} is not a subclass of fabll.Node"
        ) from e


def build(
    app: fabll.Node | None = None, ctx: BuildStepContext | None = None
) -> fabll.Node:
    """Build the project.

    Args:
        app: Optional pre-instantiated app node
        ctx: Optional build context to use (allows caller to access completed_stages)

    Returns:
        The built app node
    """
    if ctx is None:
        ctx = BuildStepContext(build=None, app=app)
    else:
        ctx.app = app
    run_build_targets(ctx)
    return ctx.require_app()


def init_app() -> fabll.Node:
    """
    Instantiate the app graph with the minimal build steps.

    This is intended for graph export/visualization tooling.
    """
    from atopile.build_steps import muster

    ctx = BuildStepContext(build=None, app=None)
    for target in muster.select({"post-instantiation-setup"}):
        target(ctx)
    return ctx.require_app()

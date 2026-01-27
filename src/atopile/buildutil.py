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
from atopile.errors import UserToolNotAvailableError
from atopile.exceptions import accumulate
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

    def flush_stages_to_db(self) -> None:
        """Write current stages to the build history database."""
        if not self.build_id:
            return
        try:
            from atopile.dataclasses import Build, BuildStatus
            from atopile.model.sqlite import BuildHistory

            stages = [s.model_dump(by_alias=True) for s in self.completed_stages]
            BuildHistory.set(Build(
                build_id=self.build_id,
                name=config.build.name,
                display_name=config.build.name,
                project_root=str(config.project.paths.root),
                target=config.build.name,
                status=BuildStatus.BUILDING,
                stages=stages,
            ))
        except Exception:
            pass  # Don't fail the build if DB write fails


@once
def _check_kicad_cli() -> bool:
    with contextlib.suppress(Exception):
        from kicadcliwrapper.generated.kicad_cli import kicad_cli

        kicad_cli(kicad_cli.version()).exec()
        return True

    return False


def run_build_targets(ctx: BuildStepContext) -> None:
    """Run build targets in dependency order."""
    from atopile import build_steps

    targets = {build_steps.generate_default.name} | set(config.build.targets) - set(
        config.build.exclude_targets
    )

    with accumulate() as accumulator:
        for target in build_steps.muster.select(targets):
            if target.name in config.build.exclude_targets:
                logger.warning(f"Skipping excluded build step '{target.name}'")
                continue

            if (
                build_steps.Tags.REQUIRES_KICAD in target.tags
                and not _check_kicad_cli()
            ):
                if target.implicit:
                    logger.warning(
                        f"Skipping target '{target.name}' because kicad-cli "
                        "was not found"
                    )
                    continue
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

import contextlib
import logging

import faebryk.library._F as F
from atopile import layout
from atopile.build_steps import Tags, muster
from atopile.cli.logging_ import LoggingStage
from atopile.config import config
from atopile.errors import UserToolNotAvailableError
from faebryk.core.cpp import set_max_paths
from faebryk.core.module import Module
from faebryk.core.pathfinder import MAX_PATHS
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.nullsolver import NullSolver
from faebryk.libs.app.erc import needs_erc_check
from faebryk.libs.exceptions import accumulate
from faebryk.libs.util import ConfigFlag, once

logger = logging.getLogger(__name__)


SKIP_SOLVING = ConfigFlag("SKIP_SOLVING", default=False)


@once
def _check_kicad_cli() -> bool:
    with contextlib.suppress(Exception):
        from kicadcliwrapper.generated.kicad_cli import kicad_cli

        kicad_cli(kicad_cli.version()).exec()
        return True

    return False


def build(app: Module) -> None:
    """Build the project."""
    if SKIP_SOLVING:
        logger.warning("Assertion checking is disabled")
        solver = NullSolver()
    else:
        solver = DefaultSolver()

    app.add(F.has_solver(solver))

    # Attach PCBs to entry points
    pcb = F.PCB(config.build.paths.layout)
    app.add(F.PCB.has_pcb(pcb))
    layout.attach_sub_pcbs_to_entry_points(app)

    # TODO remove, once erc split up
    app.add(needs_erc_check())

    # TODO remove hack
    # Disables children pathfinding
    # ```
    # power1.lv ~ power2.lv
    # power1.hv ~ power2.hv
    # -> power1 is not connected power2
    # ```
    set_max_paths(int(MAX_PATHS), 0, 0)

    targets = muster.select(
        set(config.build.targets) - set(config.build.exclude_targets)
    )

    with accumulate() as accumulator:
        for target in targets:
            if target.virtual:
                continue

            if target.name in config.build.exclude_targets:
                logger.warning(f"Skipping excluded build step '{target.name}'")
                continue

            with LoggingStage(
                target.name,
                target.description or f"Building [green]'{target.name}'[/green]",
            ) as log_context:
                if Tags.REQUIRES_KICAD in target.tags and not _check_kicad_cli():
                    if target.implicit:
                        logger.warning(
                            f"Skipping target '{target.name}' because kicad-cli was not"
                            " found",
                        )
                        continue
                    else:
                        raise UserToolNotAvailableError("kicad-cli not found")

                with accumulator.collect():
                    target(app, solver, pcb, log_context)

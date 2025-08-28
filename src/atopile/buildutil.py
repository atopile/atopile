import contextlib
import logging

import faebryk.library._F as F
from atopile.build_steps import Tags, muster
from atopile.build_steps import default as default_target
from atopile.cli.logging_ import LoggingStage
from atopile.config import config
from atopile.errors import UserToolNotAvailableError
from faebryk.core.module import Module
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.nullsolver import NullSolver
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

    pcb = F.PCB(config.build.paths.layout)

    targets = muster.select(
        {default_target.name}
        | set(config.build.targets) - set(config.build.exclude_targets)
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

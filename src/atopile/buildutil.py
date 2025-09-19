import contextlib
import logging

import faebryk.library._F as F
from atopile.build_steps import Tags, muster
from atopile.build_steps import generate_default as default_target
from atopile.config import config
from atopile.errors import UserToolNotAvailableError
from faebryk.core.module import Module
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.nullsolver import NullSolver
from faebryk.core.trait import Trait
from faebryk.libs.exceptions import accumulate
from faebryk.libs.util import ConfigFlag, once

import sys
import os
# Add the project root to Python path to import from examples
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from examples.i2c.config_traits import is_project

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

    targets = {default_target.name} | set(config.build.targets) - set(
        config.build.exclude_targets
    )

    with accumulate() as accumulator:
        for target in muster.select(targets):
            if target.name in config.build.exclude_targets:
                logger.warning(f"Skipping excluded build step '{target.name}'")
                continue

            if Tags.REQUIRES_KICAD in target.tags and not _check_kicad_cli():
                if target.implicit:
                    logger.warning(
                        f"Skipping target '{target.name}' because kicad-cli "
                        "was not found"
                    )
                    continue
                else:
                    raise UserToolNotAvailableError("kicad-cli not found")
            with accumulator.collect():
                target(app, solver, pcb) 

    # Look for is_project trait by class name since ato-imported traits have different class hierarchy
    project_traits = [t for t in app.get_children(direct_only=True, types=Trait) if t.__class__.__name__ == 'is_project']
    project_trait = project_traits[0]

    major_value = project_trait.required_atopile_version.major.try_get_literal()
    minor_value = project_trait.required_atopile_version.minor.try_get_literal()
    patch_value = project_trait.required_atopile_version.patch.try_get_literal()

    logger.info(f"Required atopile version: {major_value}.{minor_value}.{patch_value}")




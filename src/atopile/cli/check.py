import logging
import sys
from typing import List, Tuple, Dict

import click

from atopile.cli.common import ingest_config_hat
from atopile.parser.parser import build_model as build_model
from atopile.project.config import BuildConfig
from atopile.project.project import Project
from atopile.targets.targets import (
    Target,
    TargetCheckResult,
    TargetNotFoundError,
    find_target,
)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.command()
@ingest_config_hat
@click.option("--target", multiple=True, default=None)
@click.option("--debug/--no-debug", default=None)
@click.option("--strict/--no-strict", default=None)
def check(project: Project, build_config: BuildConfig, target: Tuple[str], debug: bool, strict: bool):
    if debug:
        import atopile.parser.parser
        atopile.parser.parser.log.setLevel(logging.DEBUG)

    if strict is None:
        strict = False

    model = build_model(project, build_config)

    # ensure targets
    target_names = target
    if not target_names:
        target_names: List[str] = build_config.targets

    # find targets
    targets: List[Target] = []
    for target_name in target_names:
        try:
            targets.append(find_target(target_name)(project, model, build_config))
        except TargetNotFoundError:
            log.error(f"Target {target_name} not found. Attempting to generate remaining targets.")

    # check targets
    check_results: Dict[Target, TargetCheckResult] = {}
    for target in targets:
        assert isinstance(target, Target)
        result = check_results[target] = target.check()
        # TODO: move this repeated code somewhere common
        if result == TargetCheckResult.UNSOLVABLE:
            log.error(f"Target {target.name} is unsolvable. Attempting to generate remaining targets.")
            targets.remove(target)
        elif result == TargetCheckResult.SOLVABLE:
            log.warning(f"Target {target.name} is solvable, but is unstable. Use `ato resolve {target.name}` to stabalise as desired.")
        elif result == TargetCheckResult.UNTIDY:
            log.warning(f"Target {target.name} is solvable, but is untidy.")
        elif result == TargetCheckResult.COMPLETE:
            log.info(f"Target {target.name} passes check.")

    # exit with code reflecting checks
    if strict:
        passable_check_level = TargetCheckResult.UNTIDY
    else:
        passable_check_level = TargetCheckResult.SOLVABLE

    if all(r <= passable_check_level for r in check_results.values()):
        log.info("All checks passed.")
        sys.exit(0)
    else:
        log.error(f"Targets failed {'strict' if strict else 'lenient'} checks.")
        sys.exit(1)

import logging
import sys
from typing import List, Tuple

import click

from atopile.cli.common import ingest_config_hat
from atopile.parser.parser import build_model as build_model
from atopile.project.config import BuildConfig
from atopile.project.project import Project
from atopile.targets.targets import Target, TargetCheckResult, TargetMuster

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.command()
@ingest_config_hat
@click.option("--target", multiple=True, default=None)
@click.option("--debug/--no-debug", default=None)
@click.option("--strict/--no-strict", default=None)
def build(project: Project, build_config: BuildConfig, target: Tuple[str], debug: bool, strict: bool):
    # input sanitisation
    if debug:
        import atopile.parser.parser
        atopile.parser.parser.log.setLevel(logging.DEBUG)

    if strict is None:
        strict = False

    target_names = target
    if not target_names:
        target_names: List[str] = build_config.targets

    # build core model
    model = build_model(project, build_config)
    exit_code = 0

    # generate targets
    target_muster = TargetMuster(project, model, build_config)
    target_muster.try_add_targets(target_names)

    # check targets
    if strict:
        passable_check_level = TargetCheckResult.UNTIDY
    else:
        passable_check_level = TargetCheckResult.SOLVABLE

    for target in target_muster.targets:
        assert isinstance(target, Target)
        result = target.check()
        if result > passable_check_level:
            exit_code = 1
        if result == TargetCheckResult.UNSOLVABLE:
            log.error(f"Target {target.name} is unsolvable. Attempting to generate remaining targets.")
            target_muster.targets.remove(target)
        elif result == TargetCheckResult.SOLVABLE:
            log.warning(f"Target {target.name} is solvable, but is unstable. Use `ato resolve {target.name}` to stabalise as desired.")
        elif result == TargetCheckResult.UNTIDY:
            log.warning(f"Target {target.name} is solvable, but is untidy.")
        elif result == TargetCheckResult.COMPLETE:
            log.info(f"Target {target.name} passes check.")

    # generate targets
    log.info(f"Writing build output to {project.config.paths.build}")
    project.ensure_build_dir()
    targets_string = ", ".join(target_names)
    log.info(f"Generating targets {targets_string}")
    for target in target_muster.targets:
        assert isinstance(target, Target)
        target.build()

    if exit_code == 0:
        log.info("All checks passed.")
        sys.exit(0)
    else:
        log.error("Targets failed.")
        sys.exit(1)

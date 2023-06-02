import logging
from typing import List, Tuple

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
def resolve(project: Project, build_config: BuildConfig, target: Tuple[str], debug: bool):
    if debug:
        import atopile.parser.parser
        atopile.parser.parser.log.setLevel(logging.DEBUG)

    model = build_model(project, build_config)

    log.info(f"Writing build output to {project.config.paths.build}")
    project.ensure_build_dir()

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
    for target in targets:
        assert isinstance(target, Target)
        target.resolve()

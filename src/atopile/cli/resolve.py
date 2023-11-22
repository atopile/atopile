import logging

import click

from atopile.cli.common import ingest_config_hat
from atopile.parser.parser import build_model
from atopile.project.project import Project
from atopile.targets.targets import (
    Target,
    TargetMuster,
)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.command()
@ingest_config_hat
@click.option("--debug/--no-debug", default=None)
@click.option("--clean/--no-clean", default=None)
def resolve(project: Project, debug: bool, clean: bool):
    """
    Resolve the required inputs for the specified --target(s) or the targets specified by the build config.
    Specify the root source file with the argument SOURCE.
    eg. `ato resolve --target my_target path/to/source.ato:module.path`
    """
    # input sanitisation
    if debug:
        import atopile.parser.parser
        atopile.parser.parser.log.setLevel(logging.DEBUG)

    # build core model
    model = build_model(project)

    # generate targets
    target_muster = TargetMuster.from_project_and_model(project, model)

    # check targets
    for target in target_muster.targets:
        assert isinstance(target, Target)
        target.resolve(clean=clean)

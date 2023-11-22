import logging
import sys

import click

from atopile.cli.common import ingest_config_hat
from atopile.parser.parser import build_model
from atopile.project.project import Project
from atopile.targets.targets import Target, TargetCheckResult, TargetMuster

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.command()
@ingest_config_hat
@click.option("--debug/--no-debug", default=None)
@click.option("--strict/--no-strict", default=None)
def build(
    project: Project,
    debug: bool,
    strict: bool,
):
    """
    Build the specified --target(s) or the targets specified by the build config.
    Specify the root source file with the argument SOURCE.
    eg. `ato build --target my_target path/to/source.ato:module.path`
    """
    # input sanitisation
    if debug:
        import atopile.parser.parser  # pylint: disable=import-outside-toplevel

        atopile.parser.parser.log.setLevel(logging.DEBUG)

    if strict is None:
        strict = False

    # build core model
    model = build_model(project)
    exit_code = 0

    # generate targets
    target_muster = TargetMuster.from_project_and_model(project, model)

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
            log.error(
                "Target %s is unsolvable. Attempting to generate remaining targets.",
                target.name,
            )
            target_muster.targets.remove(target)
        elif result == TargetCheckResult.SOLVABLE:
            log.warning(
                "Target %s is solvable, but is unstable. Use `ato resolve --build-config=%s --target=%s %s` to stabalise as desired.",
                target.name,
                project.config.selected_build_name,
                target.name,
                project.root,
            )
        elif result == TargetCheckResult.UNTIDY:
            log.warning("Target %s is solvable, but is untidy.", target.name)
        elif result == TargetCheckResult.COMPLETE:
            log.info("Target %s passes check.", target.name)

    # generate targets
    build_path = project.config.selected_build.build_path
    log.info("Writing build output to %s", build_path)
    build_path.mkdir(parents=True, exist_ok=True)

    targets_string = ", ".join(target.name for target in target_muster.targets)
    log.info("Generating targets %s", targets_string)
    for target in target_muster.targets:
        assert isinstance(target, Target)
        target.build()

    if exit_code == 0:
        log.info("All checks passed.")
        sys.exit(0)
    else:
        log.error("Targets failed.")
        sys.exit(1)

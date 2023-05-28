import logging
from pathlib import Path
from typing import List, Tuple, Set

import click

from atopile.resolvers.resolver import find_resolver, Resolver
from atopile.targets.targets import find_target, TargetNotFoundError, Target
from atopile.parser.parser import build_model as build_model
from atopile.project.config import BuildConfig
from atopile.project.project import Project

from .common import ingest_config_hat

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@click.command()
@ingest_config_hat
@click.option("--output", default=None)
@click.option("--target", multiple=True, default=None)
@click.option("--debug/--no-debug", default=None)
def build(project: Project, build_config: BuildConfig, target: Tuple[str], debug: bool):
    if debug:
        import atopile.parser.parser
        atopile.parser.parser.log.setLevel(logging.DEBUG)

    model = build_model(project, build_config)

    # figure out where to put everything
    # TODO: reinstate this functionality
    # if output is None:
    #     output: Path = project.config.paths.build
    # else:
    #     output: Path = Path(output)
    # if output.exists():
    #     if not output.is_dir():
    #         raise click.ClickException(f"{output} exists, but is not a directory")
    # else:
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

    # do resolution
    resolvers: Set[Resolver] = set()
    for target in targets:
        assert isinstance(target, Target)
        for resolver_name in target.required_resolvers:
            resolvers.add(find_resolver(resolver_name)(project, model, build_config))

    for resolver in resolvers:
        assert isinstance(resolver, Resolver)
        resolver.run()

    # generate targets
    targets_string = ", ".join(target_names)
    log.info(f"Generating targets {targets_string}")
    for target in targets:
        assert isinstance(target, Target)
        target.generate()

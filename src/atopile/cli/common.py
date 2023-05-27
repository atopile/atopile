import functools
import logging
from pathlib import Path

import click

from atopile.parser.parser import build_model as build_model
from atopile.project.config import BuildConfig, CustomBuildConfig
from atopile.project.project import Project

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def project_argument(f):
    def callback(ctx: click.Context, param, value):
        if value is None:
            project_path = Path.cwd()
        else:
            project_path = Path(value)

        try:
            project: Project = Project.from_path(project_path)
        except FileNotFoundError as e:
            raise click.BadParameter(f"Could not find project at {project_path}.") from e
        log.info(f"Using project {project.root}")

        ctx.obj = project
        return project

    # TODO: add help
    return click.argument("project", required=False, default=None, callback=callback)(f)

def ingest_config_hat(f):
    # to calculate the config, we need a project and we need them in that order.
    # click doesn't guarentee the order of processing, and it's substantiall up to the user entering the options.
    # since we always need the project to figure out the config, we may as well decorate the command ourselves,
    # process things in the right order and hand them back as kw_args

    @project_argument
    @click.option("--build-config", default=None)
    @click.option("--root-file", default=None)
    @click.option("--root-node", default=None)
    @functools.wraps(f)
    def wrapper(*args, project: Project, build_config: str, root_file: str, root_node: str, **kwargs):
        if build_config is None:
            build_config: BuildConfig = project.config.build.default_config
        else:
            for build_config in project.config.build.configs:
                if build_config.name == build_config:
                    break
            else:
                raise click.BadParameter(f"Could not find build-config \"{build_config}\".")
        log.info(f"Using build config {build_config.name}")

        # root-file
        if root_file is not None:
            build_config = CustomBuildConfig.from_build_config(build_config)
            build_config.root_file = project.root / root_file

        if build_config.root_file is None:
            raise click.BadParameter(f"No root-file specified by options or config \"{build_config.name}\"")

        if not build_config.root_file.exists():
            raise click.ClickException(f"root-file {root_file} does not exist")
        log.info(f"Using root-file {root_file}")

        # root-node
        if root_node is not None:
            build_config = CustomBuildConfig.from_build_config(build_config)
            build_config.root_node = root_node

        if build_config.root_node is None:
            raise click.BadParameter(f"No root-node specified by options or config \"{build_config.name}\"")

        # do the thing
        return f(*args, project, build_config, **kwargs)

    return wrapper

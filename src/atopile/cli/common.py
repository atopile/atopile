import functools
import logging
import sys
from pathlib import Path

import click

from atopile.project.config import BuildConfig, CustomBuildConfig
from atopile.project.project import Project
from atopile.version import check_project_version

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def ingest_config_hat(f):
    # to calculate the config, we need a project and we need them in that order.
    # click doesn't guarentee the order of processing, and it's substantiall up to the user entering the options.
    # since we always need the project to figure out the config, we may as well decorate the command ourselves,
    # process things in the right order and hand them back as kw_args

    @click.argument("source", required=False, default=None)
    @click.option("--build-config", default=None)
    @click.option("--root-file", help="DEPRECATED - do not use", default=None)
    @click.option("--root-node", help="DEPRECATED - do not use", default=None)
    @functools.wraps(f)
    def wrapper(
        *args,
        source: str,
        build_config: str,
        root_file: str,
        root_node: str,
        **kwargs,
    ):
        if source is None:
            source_path = Path.cwd()
            module_path = None
        else:
            split_source = source.split(":")
            if len(split_source) == 2:
                raw_source_path, module_path = split_source
            elif len(split_source) == 1:
                raw_source_path = split_source[0]
                module_path = None
            else:
                raise click.BadParameter(
                    f"Could not parse source path {source}. Expected format is `path/to/source.ato:module/path`."
                )

            source_path = Path(raw_source_path)

            if not source_path.exists():
                raise click.BadParameter(f"Path not found {str(source_path)}.")

        try:
            project: Project = Project.from_path(source_path)
        except FileNotFoundError as ex:
            raise click.BadParameter(
                f"Could not find project from path {str(source_path)}. Is this file path within a project?"
            ) from ex

        log.info("Using project %s", project.root)

        # FIXME: remove deprecated options
        if root_file is not None or root_node is not None:
            log.warning("Specifying root-file or root-node via options is deprecated.")
            log.warning("... because it was a daft idea. Matt's sorry.")
            log.warning(
                "Please instead specify what you are pointing to with a positional argument eg."
            )
            log.warning(
                "ato ... %s/%s:%s",
                project.root.relative_to(Path(".").resolve().absolute()),
                root_file,
                root_node,
            )
            log.warning("See `atopile view --help` for more information.")

        if module_path or source_path.is_file():
            root_file_path = project.standardise_import_path(source_path)
            root_node_path = str(root_file_path) + ":" + module_path
        else:
            root_file_path = None
            root_node_path = None

        if build_config is None:
            base_build_config_obj: BuildConfig = project.config.builds["default"]
        else:
            if build_config in project.config.builds:
                base_build_config_obj = project.config.builds[build_config]
            else:
                raise click.BadParameter(
                    f'Could not find build-config "{build_config}".'
                )
        if root_file_path is not None:
            build_config_obj = CustomBuildConfig.from_build_config(
                base_build_config_obj
            )
            build_config_obj.root_file = (
                (project.root / root_file_path).resolve().absolute()
            )
            if root_node_path is not None:
                build_config_obj.root_node = root_node_path
        else:
            if root_node_path is not None:
                raise click.BadParameter(
                    "Cannot specify root-node without specifying root-file via positional argument."
                )
            build_config_obj = base_build_config_obj
        log.info("Using build config %s", build_config_obj.name)

        # perform pre-build checks
        if not check_project_version(project):
            sys.exit(1)

        # do the thing
        return f(*args, project, build_config_obj, **kwargs)

    return wrapper

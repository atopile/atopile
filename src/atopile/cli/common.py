"""
Common CLI writing utilities.
"""

import functools
import itertools
import logging
from pathlib import Path
from typing import Iterable

import click
from omegaconf import OmegaConf
from omegaconf.errors import InterpolationToMissingValueError

from atopile import address, errors, version
from atopile.address import AddrStr
from atopile.config import (
    Config,
    get_project_config_from_addr,
    get_project_config_from_path,
)

log = logging.getLogger(__name__)


def project_options(f):
    """
    Utility decorator to ingest common config options to build a project.
    """

    @click.argument("entry", required=False, default=None)
    @click.option("-b", "--build", default=None)
    @click.option("-c", "--config", multiple=True)
    @click.option("-t", "--target", multiple=True)
    @functools.wraps(f)
    def wrapper(
        *args,
        entry: str,
        build: str,
        config: Iterable[str],
        target: Iterable[str],
        **kwargs,
    ):
        """Wrap a CLI command to ingest common config options to build a project."""
        # basic the entry address if provided, otherwise leave it as None
        if entry is not None:
            entry = AddrStr(entry)

            if address.get_file(entry) is None:
                raise click.BadParameter(
                    f"Invalid entry address {entry} - entry must specify a file.",
                    param_hint="entry",
                )

        # get the project
        if entry is None:
            entry_arg_file_path = Path.cwd()
        else:
            entry_arg_file_path = (
                Path(address.get_file(entry)).expanduser().resolve().absolute()
            )

        try:
            project_config = get_project_config_from_addr(str(entry_arg_file_path))
        except FileNotFoundError as ex:
            # FIXME: this raises an exception when the entry is not in a project
            raise click.BadParameter(
                f"Could not find project from path {str(entry_arg_file_path)}. Is this file path within a project?"
            ) from ex

        log.info("Using project %s", project_config.paths.project)
        # layer on selected targets
        if target:
            project_config.selected_build.targets = list(target)

        # set the build config
        if build is not None:
            if build not in project_config.builds:
                raise click.BadParameter(
                    f'Could not find build-config "{build}". Available build configs are: {", ".join(project_config.builds.keys())}.'
                )
            selected_build_name = build
            log.info("Selected build: %s", selected_build_name)

        # add custom config overrides
        if config:
            cli_conf = OmegaConf.from_dotlist(config)
        else:
            cli_conf = OmegaConf.create()

        # finally smoosh them all back together like a delicious cake
        # FIXME: why are we smooshing this -> does this need to be mutable?
        config = OmegaConf.merge(project_config, cli_conf)

        # layer on the selected addrs config
        if entry:
            if entry_arg_file_path.is_file():
                if entry_section := address.get_entry_section(entry):
                    config.selected_build.abs_entry = address.from_parts(
                        str(entry_arg_file_path.absolute()),
                        entry_section,
                    )
                else:
                    raise click.BadParameter(
                        "If an entry of a file is specified, you must specify"
                        " the node within it you want to build.",
                        param_hint="entry",
                    )
            elif entry_arg_file_path.is_dir():
                pass  # ignore this case, we'll use the entry point in the ato.yaml
            elif not entry_arg_file_path.exists():
                raise click.BadParameter(
                    "The entry you have specified does not exist.",
                    param_hint="entry",
                )
            else:
                raise ValueError(
                    f"Unexpected entry path type {entry_arg_file_path} - this should never happen!"
                )

        # ensure we have an entry-point
        try:
            config.selected_build.abs_entry
        except InterpolationToMissingValueError as ex:
            raise click.BadParameter("No entry point to build from!") from ex

        # do the thing
        return f(*args, **kwargs, config=config)

    return wrapper


def check_compiler_versions(config: Config):
    """Check that the compiler version is compatible with the version used to build the project."""
    with errors.handle_ato_errors():
        dependency_cfgs = (
            errors.downgrade(get_project_config_from_path, FileNotFoundError)(p)
            for p in Path(config.paths.abs_module_path).glob("*")
        )

        for cltr, cfg in errors.iter_through_errors(
            itertools.chain([config], dependency_cfgs)
        ):
            if cfg is None:
                continue

            with cltr():
                semver_str = cfg.ato_version
                # FIXME: this is a hack to the moment to get around us breaking
                # the versioning scheme in the ato.yaml files
                for operator in version.OPERATORS:
                    semver_str = semver_str.replace(operator, "")

                built_with_version = version.parse(semver_str)

                if not version.match_compiler_compatability(built_with_version):
                    raise version.VersionMismatchError(
                        f"{cfg.paths.project} can't be built with this version of atopile."
                    )

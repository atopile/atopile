import functools
import logging
from pathlib import Path
from typing import Iterable

import click
from omegaconf import OmegaConf
from omegaconf.errors import InterpolationToMissingValueError

from atopile import address
from atopile.address import AddrStr
from atopile.config import get_project_config_from_addr

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


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
        # basic the entry address if provided, otherwise leave it as None
        if entry is not None:
            entry = AddrStr(entry)

            if address.get_file(entry) is None:
                raise click.BadParameter(
                    f"Invalid entry address {entry} - entry must specify a file.",
                    param_hint="entry",
                )

        # get the project
        try:
            if entry is None:
                entry_arg_file_path = Path.cwd()
            else:
                entry_arg_file_path = Path(address.get_file(entry)).expanduser().resolve().absolute()

            project_config = get_project_config_from_addr(str(entry_arg_file_path))

            log.info("Using project %s", project_config.paths.project)
            # layer on selected targets
            if target:
                project_config.selected_build.targets = list(target)
        except FileNotFoundError as ex:
            raise click.BadParameter(
                f"Could not find project from path {str(address.get_file(entry))}. Is this file path within a project?"
            ) from ex

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

        # # layer on the selected addrs config
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

        # ensure we have an entry-point
        try:
            config.selected_build.abs_entry
        except InterpolationToMissingValueError as ex:
            raise click.BadParameter("No entry point to build from!") from ex

        # do the thing
        return f(*args, **kwargs, config=config)

    return wrapper

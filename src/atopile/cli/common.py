"""
Common CLI writing utilities.
"""

import functools
import itertools
import logging
from pathlib import Path
from typing import Iterable

import click

import atopile.config
from atopile import address, errors, version
from atopile.address import AddrStr

log = logging.getLogger(__name__)


def project_options(f):
    """
    Utility decorator to ingest common config options to build a project.
    """

    @click.argument("entry", required=False, default=None)
    @click.option("-b", "--build", multiple=True, envvar="ATO_BUILD")
    @click.option("-t", "--target", multiple=True, envvar="ATO_TARGET")
    @click.option("-o", "--option", multiple=True, envvar="ATO_OPTION")
    @functools.wraps(f)
    @errors.muffle_fatalities()
    @errors.log_ato_errors()
    def wrapper(
        *args,
        entry: str,
        build: Iterable[str],
        target: Iterable[str],
        option: Iterable[str],
        **kwargs,
    ):
        """Wrap a CLI command to ingest common config options to build a project."""

        # basic the entry address if provided, otherwise leave it as None
        if entry is not None:
            entry = AddrStr(entry)

            if address.get_file(entry) is None:
                raise errors.AtoBadParameterError(
                    f"Invalid entry address {entry} - entry must specify a file.",
                    title="Bad 'entry' parameter",
                )

        # get the project
        if entry is None:
            entry_arg_file_path = Path.cwd()
        else:
            entry_arg_file_path = (
                Path(address.get_file(entry)).expanduser().resolve().absolute()
            )

        try:
            project_config = atopile.config.get_project_config_from_addr(str(entry_arg_file_path))
        except FileNotFoundError as ex:
            # FIXME: this raises an exception when the entry is not in a project
            raise errors.AtoBadParameterError(
                f"Could not find project from path {str(entry_arg_file_path)}. "
                "Is this file path within a project?"
            ) from ex

        # Make sure I an all my sub-configs have appropriate versions
        check_compiler_versions(project_config)

        log.info("Using project %s", project_config.location)

        # add custom config overrides
        if option:
            raise NotImplementedError(
                "Custom config overrides have been removed in a refactor. "
                "It's planned to re-add them in a future release. "
                "If this is a blocker for you, please raise an issue. "
                "In the meantime, you can use the `ato.yaml` file to set these options."
            )
        else:
            config: atopile.config.ProjectConfig = project_config

        # if we set an entry-point, we now need to deal with that
        entry_addr_override = None
        if entry:
            if entry_arg_file_path.is_file():
                if entry_section := address.get_entry_section(entry):
                    entry_addr_override = address.from_parts(
                        str(entry_arg_file_path.absolute()),
                        entry_section,
                    )
                else:
                    raise errors.AtoBadParameterError(
                        "If an entry of a file is specified, you must specify"
                        " the node within it you want to build.",
                        title="Bad 'entry' parameter",
                    )

            elif entry_arg_file_path.is_dir():
                pass

            elif not entry_arg_file_path.exists():
                raise errors.AtoBadParameterError(
                    "The entry you have specified does not exist.",
                    title="Bad 'entry' parameter",
                )
            else:
                raise ValueError(
                    f"Unexpected entry path type {entry_arg_file_path} - this should never happen!"
                )

        # Configure project context
        project_ctx = atopile.config.ProjectContext.from_config(config)
        atopile.config.set_project_context(project_ctx)

        # Make build contexts
        with errors.handle_ato_errors(), errors.log_ato_errors():
            if build_names := build or config.builds.keys():
                build_ctxs: list[atopile.config.BuildContext] = [
                    atopile.config.BuildContext.from_config_name(config, build_name)
                    for build_name in build_names
                ]
            else:
                build_ctxs = [atopile.config.BuildContext.from_config(
                    "default",
                    atopile.config.ProjectBuildConfig(),
                    project_ctx
                )]

        for build_ctx in build_ctxs:
            if entry_addr_override is not None:
                build_ctx.entry = entry_addr_override
            if target:
                build_ctx.targets = list(target)

        # Do the thing
        return f(*args, **kwargs, build_ctxs=build_ctxs)

    return wrapper


def check_compiler_versions(config: atopile.config.ProjectConfig):
    """
    Check that the compiler version is compatible with the version
    used to build the project.
    """
    with errors.handle_ato_errors():
        dependency_cfgs = (
            errors.downgrade(atopile.config.get_project_config_from_path, FileNotFoundError)(p)
            for p in Path(config.location).glob("*")
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
                        f"{cfg.location} ({cfg.ato_version}) can't be"
                        " built with this version of atopile "
                        f"({version.get_installed_atopile_version()})."
                    )

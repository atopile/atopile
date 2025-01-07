"""
Common CLI writing utilities.
"""

import itertools
import logging
from pathlib import Path
from typing import Iterable

import faebryk.libs.exceptions
from atopile import address, errors, version
from atopile.address import AddrStr
from atopile.config import BuildConfig, ProjectConfig, ProjectPaths, config

log = logging.getLogger(__name__)


def get_entry_arg_file_path(entry: str | None) -> tuple[AddrStr | None, Path]:
    # basic the entry address if provided, otherwise leave it as None

    if entry is None:
        entry_arg_file_path = Path.cwd()
    else:
        entry = AddrStr(entry)

        if address.get_file(entry) is None:
            raise errors.UserBadParameterError(
                f"Invalid entry address {entry} - entry must specify a file.",
                title="Bad 'entry' parameter",
            )

        entry_arg_file_path = (
            Path(address.get_file(entry)).expanduser().resolve().absolute()
        )

    return entry, entry_arg_file_path


def check_entry_arg_file_path(
    entry: AddrStr | None, entry_arg_file_path: Path
) -> AddrStr | None:
    entry_addr_override = None

    if entry:
        if entry_arg_file_path.is_file():
            if entry_section := address.get_entry_section(entry):
                entry_addr_override = address.from_parts(
                    str(entry_arg_file_path.absolute()),
                    entry_section,
                )
            else:
                raise errors.UserBadParameterError(
                    "If an entry of a file is specified, you must specify"
                    " the node within it you want to build.",
                    title="Bad 'entry' parameter",
                )

        elif entry_arg_file_path.is_dir():
            pass

        elif not entry_arg_file_path.exists():
            raise errors.UserBadParameterError(
                "The entry you have specified does not exist.",
                title="Bad 'entry' parameter",
            )
        else:
            raise ValueError(
                f"Unexpected entry path type {entry_arg_file_path} - this should never happen!"  # noqa: E501  # pre-existing
            )

    return entry_addr_override


def check_compiler_versions():
    """
    Check that the compiler version is compatible with the version
    used to build the project.
    """

    dependency_cfgs = (
        (dep.project_config for dep in config.project.dependencies)
        if config.project.dependencies is not None
        else ()
    )

    for cltr, cfg in faebryk.libs.exceptions.iter_through_errors(
        itertools.chain([config.project], dependency_cfgs)
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
                    f"{cfg.paths.root} ({cfg.ato_version}) can't be"
                    " built with this version of atopile "
                    f"({version.get_installed_atopile_version()})."
                )


def configure_project_context(entry: str | None, standalone: bool = False) -> None:
    # TODO: mvoe to config
    entry, entry_arg_file_path = get_entry_arg_file_path(entry)
    config.project.entry = entry

    if standalone:
        if not entry:
            raise errors.UserBadParameterError(
                "You must specify an entry to build with the --standalone option"
            )
        if not entry_arg_file_path.exists():
            raise errors.UserBadParameterError(
                f"The file you have specified does not exist: {entry_arg_file_path}"
            )

        if config.project is not None:
            # TODO: verify behaviour
            raise errors.UserBadParameterError(
                "Project config must not be present for standalone builds"
            )

        config.project_dir = Path.cwd()
        config.project = ProjectConfig(
            ato_version=f"^{version.get_installed_atopile_version()}",
            paths=ProjectPaths(
                layout=config.project_dir / "standalone",
                src=config.project_dir,
            ),
            builds={"default": BuildConfig(entry="", targets=[])},
        )

    # Make sure I an all my sub-configs have appropriate versions
    check_compiler_versions()

    log.info("Using project %s", config.project_dir)


def parse_build_options(
    entry: str | None,
    build: Iterable[str],
    target: Iterable[str],
    option: Iterable[str],
    standalone: bool,
) -> None:
    # TODO: move this to config

    entry, entry_arg_file_path = get_entry_arg_file_path(entry)

    configure_project_context(entry, standalone)

    # These checks are only relevant if we're **building** standalone
    # TODO: Some of the contents should be moved out of the project context
    if standalone:
        if not entry_arg_file_path.is_file():
            raise errors.UserBadParameterError(
                "The path you're building with the --standalone"
                f" option must be a file {entry_arg_file_path}"
            )
        assert entry is not None  # Handled by configure_project_context
        if not address.get_entry_section(entry):
            raise errors.UserBadParameterError(
                "You must specify what to build within a file to build with the"
                " --standalone option"
            )

    # add custom config overrides
    if option:
        raise errors.UserNotImplementedError(
            "Custom config overrides have been removed in a refactor. "
            "It's planned to re-add them in a future release. "
            "If this is a blocker for you, please raise an issue. "
            "In the meantime, you can use the `ato.yaml` file to set these options."
        )

    # if we set an entry-point, we now need to deal with that
    entry_addr_override = check_entry_arg_file_path(entry, entry_arg_file_path)

    if build:
        config.builds = list(build)

    for build_name in config.builds:
        try:
            build_config = config.project.builds[build_name]
        except KeyError:
            raise errors.UserBadParameterError(
                f"Build `{build_name}` not found in project config"
            )
        if entry_addr_override is not None:
            build_config.address = entry_addr_override
        if target:
            build_config.targets = list(target)

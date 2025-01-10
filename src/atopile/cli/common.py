"""
Common CLI writing utilities.
"""

import logging
from pathlib import Path
from typing import Iterable

from atopile import address, errors
from atopile.address import AddrStr
from atopile.config import config

log = logging.getLogger(__name__)


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


def parse_build_options(
    entry: str | None,
    selected_builds: Iterable[str],
    target: Iterable[str],
    option: Iterable[str],
    standalone: bool,
) -> None:
    # TODO: move this to config

    entry, entry_arg_file_path = get_entry_arg_file_path(entry)
    config.apply_options(entry, entry_arg_file_path, standalone)

    # These checks are only relevant if we're **building** standalone
    # TODO: Some of the contents should be moved out of the project context
    if standalone:
        if not entry_arg_file_path.is_file():
            raise errors.UserBadParameterError(
                "The path you're building with the --standalone"
                f" option must be a file {entry_arg_file_path}"
            )
        assert entry is not None  # Handled by config.apply_build_options
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

    if selected_builds:
        config.selected_builds = list(selected_builds)

    for build_name in config.selected_builds:
        if build_name not in config.project.builds:
            raise errors.UserBadParameterError(
                f"Build `{build_name}` not found in project config"
            )

        if entry_addr_override is not None:
            config.project.builds[build_name].address = entry_addr_override
        if target:
            config.project.builds[build_name].targets = list(target)

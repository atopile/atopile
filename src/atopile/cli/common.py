"""
Common CLI writing utilities.
"""

import logging
from pathlib import Path

from atopile import address, errors
from atopile.address import AddrStr

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

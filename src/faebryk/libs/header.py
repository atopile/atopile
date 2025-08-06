# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
import re

import black
import black.parsing

logger = logging.getLogger(__name__)


def get_header():
    return (
        "# This file is part of the faebryk project\n# SPDX-License-Identifier: MIT\n"
    )


def formatted_file_contents(file_contents: str, is_pyi: bool = False) -> str:
    try:
        return black.format_str(
            file_contents,
            mode=black.Mode(
                is_pyi=is_pyi,
            ),
        )

    except black.parsing.InvalidInput as e:
        lineno, column = None, None
        match = re.match(r"Cannot parse: (\d+):(\d+):", e.args[0])
        if match:
            lineno, column = map(int, match.groups())
        with_line_numbers = "\n".join(
            f"{'>>' if i + 1 == lineno else '  '}{i + 1:3d}: {line}"
            for i, line in enumerate(file_contents.split("\n"))
        )
        logger.warning("black failed to format file:\n" + with_line_numbers)
        raise

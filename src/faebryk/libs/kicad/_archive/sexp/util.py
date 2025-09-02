# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from collections import deque
from pathlib import Path

import typer

logger = logging.getLogger(__name__)


def prettify_sexp_string(raw: str) -> str:
    """
    Prettify an S-expression string by adding proper indentation and line breaks.

    S-expressions (symbolic expressions) are a notation for nested list-like data
    structures, commonly used in formats like KiCad files. This function takes a raw,
    potentially single-line or poorly formatted S-expression and formats it for better
    readability.

    Formatting rules applied:
    - Each nested level gets 4 spaces of indentation
    - Opening parentheses that start new nested expressions get their own lines
    - Closing parentheses of non-leaf expressions get proper indentation
    - Consecutive spaces are collapsed to single spaces
    - Newlines in the raw input are removed and replaced with strategic line breaks
    - Content within quoted strings is preserved as-is
    - Leaf expressions (containing only simple values) stay on single lines

    Args:
        raw: The raw S-expression string to prettify

    Returns:
        A formatted S-expression string with proper indentation and line breaks

    Example:
        Input:  '(module (at 1 2) (layer "F.Cu") (tedit 123))'
        Output: '(module\n    (at 1 2)\n    (layer "F.Cu")\n    (tedit 123))'
    """
    out = deque()
    level = 0
    in_quotes = False
    in_leaf_expr = True
    for c in raw:
        if c == '"':
            in_quotes = not in_quotes
        if in_quotes:
            ...
        elif c == "\n":
            continue
        elif c == " " and out[-1] == " ":
            continue
        elif c == "(":
            in_leaf_expr = True
            if level != 0:
                if out[-1] == " ":
                    out.pop()
                out.append("\n" + " " * 4 * level)
            level += 1
        elif c == ")":
            if out[-1] == " ":
                out.pop()
            level -= 1
            if not in_leaf_expr:
                out.append("\n" + " " * 4 * level)
            in_leaf_expr = False
        out.append(c)

    # if i > 0 no strip is a kicad bug(?) workaround
    return "\n".join(
        x.rstrip() if i > 0 else x for i, x in enumerate("".join(out).splitlines())
    )


def main(path: Path, out: Path | None = None):
    if not out:
        out = path
    content = path.read_text(encoding="utf-8")
    pretty = prettify_sexp_string(content)
    out.write_text(pretty, encoding="utf-8")


if __name__ == "__main__":
    typer.run(main)

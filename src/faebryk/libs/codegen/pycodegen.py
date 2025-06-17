# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
import subprocess
from pathlib import Path
from textwrap import dedent
from typing import Callable, Iterable

import black

logger = logging.getLogger(__name__)


def sanitize_name(raw, expect_arithmetic: bool = False, warn_prefix: str | None = ""):
    sanitized = raw
    # braces
    sanitized = sanitized.replace("(", "")
    sanitized = sanitized.replace(")", "")
    sanitized = sanitized.replace("[", "")
    sanitized = sanitized.replace("]", "")
    # seperators
    sanitized = sanitized.replace(".", "_")
    sanitized = sanitized.replace(",", "_")
    sanitized = sanitized.replace("/", "_")
    sanitized = sanitized.replace(" ", "_")
    if not expect_arithmetic:
        sanitized = sanitized.replace("-", "_")

    # special symbols
    sanitized = sanitized.replace("'", "")
    sanitized = sanitized.replace("*", "")
    sanitized = sanitized.replace("^", "p")
    sanitized = sanitized.replace("#", "h")
    sanitized = sanitized.replace("ϕ", "phase")
    sanitized = sanitized.replace("π", "pi")
    sanitized = sanitized.replace("&", "and")
    # inversion
    sanitized = sanitized.replace("~", "n")
    sanitized = sanitized.replace("{", "")
    sanitized = sanitized.replace("}", "")

    sanitized = sanitized.replace("->", "to")
    sanitized = sanitized.replace("<-", "from")
    # arithmetics
    sanitized = sanitized.replace(">", "gt")
    sanitized = sanitized.replace("<", "lt")
    sanitized = sanitized.replace("=", "eq")
    sanitized = sanitized.replace("+", "plus")
    sanitized = sanitized.replace("-", "minus")

    # rest
    def handle_unknown_invalid_symbold(match):
        if warn_prefix is not None:
            logger.warning(
                f"{warn_prefix}: Replacing unknown invalid symbol"
                f" `{match.group(0)}` in `{raw}` with `_`"
            )
        return "_"

    sanitized = re.sub(r"[^a-zA-Z_0-9]", handle_unknown_invalid_symbold, sanitized)
    sanitized = re.sub(r"__+", "_", sanitized)

    if re.match("^[a-zA-Z_]", sanitized) is None:
        sanitized = "P" + sanitized

    if re.match("^[a-zA-Z_]+[a-zA-Z_0-9]*$", sanitized) is not None:
        return sanitized

    to_escape = re.findall("[^a-zA-Z_0-9]", sanitized)
    if len(to_escape) > 0:
        raise ValueError(f"Cannot sanitize name: {raw}")

    return sanitized


def gen_repeated_block[T](
    generator: Iterable[T],
    func: Callable[[T], str] = dedent,
    requires_pass: bool = False,
) -> str:
    lines = list(map(func, generator))

    if not lines and requires_pass:
        lines = ["pass"]

    return gen_block("\n".join(lines))


def gen_block(payload: str):
    return f"#__MARK_BLOCK_BEGIN\n{payload}\n#__MARK_BLOCK_END"


def fix_indent(text: str) -> str:
    indent_stack = [""]

    out_lines = []
    for line in text.splitlines():
        if "#__MARK_BLOCK_BEGIN" in line:
            indent_stack.append(line.removesuffix("#__MARK_BLOCK_BEGIN"))
        elif "#__MARK_BLOCK_END" in line:
            indent_stack.pop()
        else:
            out_lines.append(indent_stack[-1] + line)

    return dedent("\n".join(out_lines))


def format_and_write(code: str, path: Path):
    code = code.strip()
    code = black.format_file_contents(code, fast=True, mode=black.FileMode())
    path.write_text(code, encoding="utf-8")

    subprocess.check_output(["ruff", "check", "--fix", path])

# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger(__name__)


def prettify_sexp_string(raw: str) -> str:
    out = ""
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
                out += "\n" + " " * 4 * level
            level += 1
        elif c == ")":
            level -= 1
            if not in_leaf_expr:
                out += "\n" + " " * 4 * level
            in_leaf_expr = False
        out += c

    # if i > 0 no strip is a kicad bug(?) workaround
    out = "\n".join(x.rstrip() if i > 0 else x for i, x in enumerate(out.splitlines()))
    return out

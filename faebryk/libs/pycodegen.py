# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re

logger = logging.getLogger("pycodegen")


def sanitize_name(raw):
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
        logger.warning(
            "Replacing unknown invalid symbol {} in {} with _".format(
                match.group(0), raw
            )
        )
        return "_"

    sanitized = re.sub(r"[^a-zA-Z_0-9]", handle_unknown_invalid_symbold, sanitized)

    if re.match("^[a-zA-Z_]", sanitized) is None:
        sanitized = "_" + sanitized

    if re.match("^[a-zA-Z_]+[a-zA-Z_0-9]*$", sanitized) is not None:
        return sanitized

    to_escape = re.findall("[^a-zA-Z_0-9]", sanitized)
    if len(to_escape) > 0:
        return None, to_escape

    return sanitized

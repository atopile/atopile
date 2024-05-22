# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re

logger = logging.getLogger(__name__)


def prettify_sexp_string(raw: str) -> str:
    out = ""
    level = 0
    in_quotes = False
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
            if level != 0:
                out += "\n" + " " * 4 * level
            level += 1
        elif c == ")":
            level -= 1
        out += c

    # if i > 0 no strip is a kicad bug(?) workaround
    out = "\n".join(x.rstrip() if i > 0 else x for i, x in enumerate(out.splitlines()))
    return out


class multi_key_dict:
    def __init__(self, *args, **kwargs):
        self.dict_ = kwargs
        self.tuple_list = list(args)

    def items(self):
        for i in self.tuple_list:
            yield i
        for i in self.dict_.items():
            yield i

    def update(self, tuple_list, dict_):
        self.tuple_list = []
        self.dict_ = {}
        if tuple_list is not None:
            self.tuple_list = tuple_list
        if dict_ is not None:
            self.dict_ = dict_

    def __repr__(self):
        return repr(list(self.items()))

    def __len__(self):
        return len(self.tuple_list) + len(self.dict_)


def _expandable(obj):
    return type(obj) in [dict, list, tuple, multi_key_dict]


# Limitations:
# - dict only
#   -> no duplicate keys possible
def gensexp(obj):
    # Basecase
    if obj is None:
        return None

    if not _expandable(obj):
        strrepr = str(obj)
        if re.search(r"[ ()\[\]]", strrepr) is not None:
            strrepr = f'"{strrepr}"'
        return strrepr

    # Recursion
    # TODO: key with empty val

    # Dict
    if type(obj) in [dict, multi_key_dict]:
        obj = obj.items()

    sexp = " ".join(filter(lambda x: x is not None and len(x) > 0, map(gensexp, obj)))

    # if not dict [i.e. list, tuple], add parantheses
    if type(obj) in [list, tuple] and len(obj) > 0:  # type({}.items()):
        sexp = "({})".format(sexp)

    # logger.info("%s -> %s", str(obj), sexp)

    return sexp

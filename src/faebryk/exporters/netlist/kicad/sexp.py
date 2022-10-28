# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re

logger = logging.getLogger("sexp")


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
        if re.search("[ ()]", strrepr) is not None:
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

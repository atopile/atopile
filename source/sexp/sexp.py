# Copyright (c) 2021 ITENG
# SPDX-License-Identifier: MIT

import logging
from typing import Iterable

logger = logging.getLogger("sexp")

class multi_key_dict:
    def __init__(self, *args,**kwargs):
        self.dict_ = kwargs
        self.tuple_list = args

    def items(self):
        for i in self.tuple_list:
            yield i
        for i in self.dict_.items():
            yield i

    def __repr__(self):
        return repr(list(self.items()))

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
        return str(obj)

    # Recursion
    # TODO: key with empty val

    # Dict
    if type(obj) in [dict, multi_key_dict]:
        obj = obj.items() 

    sexp = " ".join(
        filter(lambda x: x is not None, 
            map(gensexp, obj)
        )
    )

    # if not dict [i.e. list, tuple], add parantheses
    if type(obj) in [list, tuple] : #type({}.items()):
        sexp = "({})".format(sexp)    
    
    #logger.info("%s -> %s", str(obj), sexp)

    return sexp

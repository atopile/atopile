# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import os

if __name__ == '__main__':
    import os
    import sys
    root = os.path.join(os.path.dirname(__file__), '../../../..')
    sys.path.append(root)

from typing import Iterable
import faebryk.exporters.netlist.kicad.sexp as sexp_gen
from faebryk.exporters.netlist.kicad.sexp import multi_key_dict
from test.deps import sexp_parser
import re
import unittest

"""
    Converts python dict to format which can be recovered by sexp without
    information loss.
    Useful for comparing equivalence of parsed and generated output.
"""
def _dict2tuple(obj):
    if type(obj) not in [dict, list, multi_key_dict]:
        return obj

    flag = []
    if type(obj) in [dict, multi_key_dict]:
        obj = list(obj.items())

        # In sexp a key having a dict value converts to
        #   the key becoming an operator and the dict value expands
        #   to a list of k,v tuples as operands
        #   if we dont unpack the list the key is an operator for a
        #   single argument, which is then the list, instead of the tuples.
        # There is likely a better way to do this, but this works for now.
        for i in range(len(obj)):
            if len(obj[i]) == 2 and type(obj[i][1]) in [dict, multi_key_dict]:
                flag += [i]


    out = [tuple(map(_dict2tuple, o)) for o in obj]

    # See comment above
    for i in flag:
        out[i] = out[i][0],*out[i][1]

    return out


"""
    Clean the parsed output of parsesexp
    Removes line numbers and converts lists to tuples
    Useful for comparing equivalence of parsed and generated output.
"""
def _cleanparsed(parsed):
    # base case
    if type(parsed) is not list:
        return parsed

    if type(parsed[0]) != type(1):
        print("Fault:", parsed)
        raise Exception

    # remove line numbers
    parsed = parsed[1:]
    for i,obj in enumerate(parsed):
        if type(obj) is str and re.match('^".+"$', obj) is not None:
            parsed[i] = obj[1:-1]
    # recurse
    parsed = tuple(map(_cleanparsed, parsed))

    return parsed


"""
    Test case
    Test whether obj -> sexp -> obj returns back same obj
"""
def _test_py2net2py(obj):
    sexp=sexp_gen.gensexp(obj)
    parsed = sexp_parser.parseSexp(sexp)
    try:
        cleaned = _cleanparsed(parsed)
    except Exception as e:
        print("Source:", sexp)
        print("Died:", parsed)
        return False

    objtuple = _dict2tuple(obj)[0]

    eq = objtuple == cleaned
    if not eq:
        print("Not equal:")
        print("\tsource\t", obj)
        print("\tdic2tup\t", objtuple)
        print("\tsexp\t", sexp)
        print("\tparsed\t", cleaned)

    return eq


"""
    Test case
    Test whether sexp -> obj -> sexp returns back same sexp
"""
def _test_net2py2net(netfilepath):
    with open(netfilepath, "r") as netfile:
        netsexp=netfile.read()
    netsexpparsed = sexp_parser.parseSexp(netsexp)
    cleaned = _cleanparsed(netsexpparsed)
    netsexpgen = sexp_gen.gensexp(cleaned)
    netsexpgenparsed = sexp_parser.parseSexp(netsexpgen)
    cleanedparsed = _cleanparsed(netsexpgenparsed)

    netsexpcleaned = netsexp
    netsexpcleaned = re.sub("\t", "", netsexpcleaned)
    netsexpcleaned = re.sub("^[ ]+", "", netsexpcleaned)
    netsexpcleaned = re.sub("[ ]+", " ", netsexpcleaned)
    netsexpcleaned = re.sub("\n", "", netsexpcleaned)

    eq_str = netsexpcleaned == netsexpgen
    eq = cleaned == cleanedparsed
    if not eq:
        print("Not equal")
        if eq_str:
            print("But strings are equal")
        else:
            print("\tSourceStr:\t", netsexpcleaned)
            print("\tGen   Str:\t",netsexpgen)
        print("\tSource   :\t", netsexpparsed)
        print("\tGen      :\t", netsexpgenparsed)

    return eq


def _test_sexp():
    testdict = {
        "testdict" :
            {
                "a": {
                    "b" : "5"
                },
                "e": {
                    "b" : "5"
                },
                "c": "d"
            }
        }

    ok = _test_py2net2py(testdict)
    if not ok:
        print("testdict:", ok)
        return ok

    testdict2 = multi_key_dict(
        ("testdict", multi_key_dict(
            ("a", multi_key_dict(
                ("b", "5"),
            )),
            ("e", multi_key_dict(
                ("b", "5")
            )),
            ("c", "d")
        ))
    )
    ok = _test_py2net2py(testdict2)
    if not ok:
        print("testdict2:", ok)
        return ok


    netlistdict = {
        "export":
            {
                "version": "D",
                "design": {
                    "source": "/home/...",
                    "date": 'Sat 13 ...',
                    "tool": 'Eeschema',
                    "sheet": {
                        "number": "1",
                        "name" : "/",
                        "tstamps": "/",
                        "title_block": multi_key_dict(
                            ("title",),
                            ("company",),
                            ("rev",),
                            ("date",),
                            ("source", "main.sch"),
                            ("comment",  {
                                "number": "1",
                                "value": "\"\""
                            }),
                            ("comment",  {
                                "number": "2",
                                "value": "\"\""
                            }),
                            ("comment",  {
                                "number": "3",
                                "value": "\"\""
                            }),
                            ("comment",  {
                                "number": "4",
                                "value": "\"\""
                            }),
                        )
                    }
                }
            }
    }

    ok = _test_py2net2py(netlistdict)
    if not ok:
        print("netlistdict:", ok)
        return ok

    ok = _test_net2py2net(os.path.join(os.path.dirname(__file__), "test.net"))
    if not ok:
        print("net2py2net:", ok)
        return ok


    return ok
    # TODO test empty dicts,lists,tuples,...


class TestSexp(unittest.TestCase):
    def test_sexp(self):
        self.assertTrue(_test_sexp())


if __name__ == '__main__':
    unittest.main()
# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import re
import unittest

import faebryk.libs.kicad.sexp as sexp_gen
import sexpdata
from faebryk.libs.kicad.sexp import multi_key_dict

logger = logging.getLogger(__name__)

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
        out[i] = out[i][0], *out[i][1]

    return out


"""
    Clean the parsed output of sexpdata
    Converts lists to tuples and gets values out of objects
    Useful for comparing equivalence of parsed and generated output.
"""


def _cleanparsed(parsed):
    # recursion
    if type(parsed) is list:
        return tuple(map(_cleanparsed, parsed))

    # basecase 1
    if isinstance(parsed, sexpdata.Symbol):
        return str(parsed.value())

    # workaround for empty strings to make sexpdata behave like sexp_parser
    if type(parsed) is str and parsed == "":
        return '""'

    # basecase 2
    return str(parsed)


"""
    Test case
    Test whether obj -> sexp -> obj returns back same obj
"""


def _test_py2net2py(obj):
    sexp = sexp_gen.gensexp(obj)
    parsed = sexpdata.loads(sexp)
    try:
        cleaned = _cleanparsed(parsed)
    except Exception:
        logger.error("Source:%s", sexp)
        logger.error("Died:%s", parsed)
        return False

    objtuple = _dict2tuple(obj)[0]

    eq = objtuple == cleaned
    if not eq:
        logger.info("Not equal:")
        logger.info("\tsource\t%s", obj)
        logger.info("\tsexp\t%s", sexp)
        logger.info("\tdic2tup\t%s", objtuple)
        logger.info("\tcleaned\t%s", cleaned)
        logger.info("\tparsed\t%s", parsed)

    return eq


"""
    Test case
    Test whether sexp -> obj -> sexp returns back same sexp
"""


def _test_net2py2net(netfilepath):
    with open(netfilepath, "r") as netfile:
        netsexp = netfile.read()
    netsexpparsed = sexpdata.loads(netsexp)
    cleaned = _cleanparsed(netsexpparsed)
    netsexpgen = sexp_gen.gensexp(cleaned)
    netsexpgenparsed = sexpdata.loads(netsexpgen)
    cleanedparsed = _cleanparsed(netsexpgenparsed)

    netsexpcleaned = netsexp
    netsexpcleaned = re.sub("\t", "", netsexpcleaned)
    netsexpcleaned = re.sub("^[ ]+", "", netsexpcleaned)
    netsexpcleaned = re.sub("[ ]+", " ", netsexpcleaned)
    netsexpcleaned = re.sub("\n", "", netsexpcleaned)

    eq_str = netsexpcleaned == netsexpgen
    eq = cleaned == cleanedparsed
    if not eq:
        logger.error("Not equal")
        if eq_str:
            logger.error("But strings are equal")
        else:
            logger.info("\tSourceStr:\t%s", netsexpcleaned)
            logger.info("\tGen   Str:\t%s", netsexpgen)
        logger.info("\tSource   :\t%s", netsexpparsed)
        logger.info("\tGen      :\t%s", netsexpgenparsed)

    return eq


def _test_sexp():
    testdict = {"testdict": {"a": {"b": "5"}, "e": {"b": "5"}, "c": "d"}}

    ok = _test_py2net2py(testdict)
    if not ok:
        logger.info("testdict:%s", ok)
        return ok

    testdict2 = multi_key_dict(
        (
            "testdict",
            multi_key_dict(
                (
                    "a",
                    multi_key_dict(
                        ("b", "5"),
                    ),
                ),
                ("e", multi_key_dict(("b", "5"))),
                ("c", "d"),
            ),
        )
    )
    ok = _test_py2net2py(testdict2)
    if not ok:
        logger.info("testdict2:%s", ok)
        return ok

    netlistdict = {
        "export": {
            "version": "D",
            "design": {
                "source": "/home/...",
                "date": "Sat 13 ...",
                "tool": "Eeschema",
                "sheet": {
                    "number": "1",
                    "name": "/",
                    "tstamps": "/",
                    "title_block": multi_key_dict(
                        ("title",),
                        ("company",),
                        ("rev",),
                        ("date",),
                        ("source", "main.sch"),
                        ("comment", {"number": "1", "value": '""'}),
                        ("comment", {"number": "2", "value": '""'}),
                        ("comment", {"number": "3", "value": '""'}),
                        ("comment", {"number": "4", "value": '""'}),
                    ),
                },
            },
        }
    }

    ok = _test_py2net2py(netlistdict)
    if not ok:
        logger.info("netlistdict:%s", ok)
        return ok

    ok = _test_net2py2net(
        os.path.join(os.path.dirname(__file__), "../../../common/resources/test.net")
    )
    if not ok:
        logger.info("net2py2net:%s", ok)
        return ok

    return ok
    # TODO test empty dicts,lists,tuples,...


class TestSexp(unittest.TestCase):
    def test_sexp(self):
        self.assertTrue(_test_sexp())


if __name__ == "__main__":
    unittest.main()

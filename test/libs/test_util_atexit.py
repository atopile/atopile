# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import sys
import unittest

from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.picker.jlcpcb.jlcpcb import JLCPCB_DB, ComponentQuery
from faebryk.libs.util import at_exit

HELLO = "Hello, World!"
BYE = "Bye, World!"


def ex():
    print(BYE)


def sync_stuff():
    print("Done")


def async_stuff():
    JLCPCB_DB.get()
    ComponentQuery().filter_by_category(
        "Instrumentation/Meter", "Tester"
    ).filter_by_lcsc_pn("92738").get()
    print("Done")


def normal():
    sync_stuff()


def exc():
    sync_stuff()
    raise Exception()


def async_normal():
    async_stuff()


def async_exc():
    async_stuff()
    raise Exception()


SWITCH = {
    0: normal,
    1: exc,
    2: async_normal,
    3: async_exc,
}


def run(i: int = 0):
    at_exit(ex)
    print(HELLO)
    SWITCH[i]()


class TestUtilAtExit(unittest.TestCase):
    @unittest.skip("Requires DB")
    def test_configs(self):
        import subprocess

        ps = [
            subprocess.Popen(
                ["python", __file__, str(i)],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            for i in SWITCH
        ]
        for i, p in enumerate(ps):
            out = p.communicate(timeout=10)
            msg = out[0].decode()
            print(i, "-" * 20)
            print(msg)
            lines = msg.splitlines()
            assert lines[-1] == BYE
            assert lines.count(BYE) == 1


# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    setup_basic_logging()

    if len(sys.argv) > 1:
        run(int(sys.argv[1]))
    else:
        unittest.main()

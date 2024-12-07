# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import time
import unittest
from itertools import combinations

from faebryk.libs.util import (
    SharedReference,
    assert_once,
    once,
    times_out,
    zip_non_locked,
)


class TestUtil(unittest.TestCase):
    def test_zip_non_locked(self):
        expected = [(1, 4), (2, 5), (3, 6)]

        for val, ref in zip(zip_non_locked([1, 2, 3], [4, 5, 6]), expected):
            self.assertEqual(val, ref)

        expected = [(1, 4), (2, 5), (2, 6)]
        for val, ref in zip((it := zip_non_locked([1, 2, 3], [4, 5, 6])), expected):
            self.assertEqual(val, ref)
            if val == (2, 5):
                it.advance(1)

    def test_shared_reference(self):
        def all_equal(*args: SharedReference):
            for left, right in combinations(args, 2):
                self.assertIs(left.links, right.links)
                self.assertIs(left(), right())
                self.assertEqual(left, right)

        r1 = SharedReference(1)
        r2 = SharedReference(2)

        self.assertEqual(r1(), 1)
        self.assertEqual(r2(), 2)

        r1.link(r2)

        all_equal(r1, r2)

        r3 = SharedReference(3)
        r3.link(r2)

        all_equal(r1, r2, r3)

        r4 = SharedReference(4)
        r5 = SharedReference(5)

        r4.link(r5)

        all_equal(r4, r5)

        r5.link(r1)

        all_equal(r1, r2, r3, r4, r5)

    def test_once(self):
        global ran
        ran = False

        @once
        def do(val: int):
            global ran
            ran = True
            return val

        self.assertFalse(ran)

        self.assertEqual(do(5), 5)
        self.assertTrue(ran)
        ran = False

        self.assertEqual(do(5), 5)
        self.assertFalse(ran)

        self.assertEqual(do(6), 6)
        self.assertTrue(ran)
        ran = False

        class A:
            @classmethod
            @once
            def do(cls):
                global ran
                ran = True
                return cls

            @once
            def do_inst(self, arg: int):
                global ran
                ran = True
                return arg

        self.assertEqual(A.do(), A)
        self.assertTrue(ran)
        ran = False

        self.assertEqual(A.do(), A)
        self.assertFalse(ran)

        ran = False
        a = A()
        self.assertEqual(a.do_inst(5), 5)
        self.assertTrue(ran)
        ran = False
        self.assertEqual(a.do_inst(5), 5)
        self.assertFalse(ran)

    def test_assert_once(self):
        class A:
            def __init__(self):
                self.a = 1

            @assert_once
            def do(self):
                print("do")
                self.a = 5

            @assert_once
            def do_with_arg(self, arg: int):
                print("do_with_arg", arg)
                self.a = arg

        a = A()
        a.do()
        self.assertEqual(a.a, 5)
        self.assertRaises(AssertionError, a.do)
        a.do_with_arg(3)
        self.assertEqual(a.a, 3)
        self.assertRaises(AssertionError, a.do_with_arg, 2)

    def test_times_out(self):
        @times_out(0.1)
        def do(wait_s: float):
            time.sleep(wait_s)

        self.assertRaises(TimeoutError, do, 0.5)
        do(0)

# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import time
import unittest
from itertools import combinations

import pytest

from faebryk.libs.util import (
    SharedReference,
    TotalOrder,
    assert_once,
    invert_dict,
    once,
    times,
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


class _DictTestObjBrokenHash:
    def __init__(self, value: object):
        self.value = value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _DictTestObjBrokenHash):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return 5


@pytest.mark.parametrize(
    "to_test, expected",
    [
        ({1: "a", 2: "b", 3: "c"}, {"a": [1], "b": [2], "c": [3]}),
        ({1: "a", 2: "a", 3: "a"}, {"a": [1, 2, 3]}),
        ({1: "a", 2: "b", 3: "a"}, {"a": [1, 3], "b": [2]}),
        (
            {
                1: (a := _DictTestObjBrokenHash("a")),
                2: (b := _DictTestObjBrokenHash("b")),
                3: a,
            },
            {a: [1, 3], b: [2]},
        ),
    ],
)
def test_invert_dict(to_test: dict, expected: dict):
    out = invert_dict(to_test)
    assert out == expected


def test_total_order_basic_int():
    order = TotalOrder[int]()
    order.add_rel(1, 2)
    order.add_rel(1, 3)
    order.add_rel(3, 4)
    expected = {
        1: [[1, 2], [1, 3, 4]],
        2: [[1, 2]],
        3: [[1, 3, 4]],
        4: [[1, 3, 4]],
    }
    assert order.get() == expected, f"Expected {expected}, got {order.get()}"


def test_total_order_basic_str():
    A, B, C, D = "A", "B", "C", "D"
    order = TotalOrder[str]()
    order.add_rel(A, B)
    order.add_rel(B, D)
    order.add_rel(C, D)
    expected = {
        A: [[A, B, D]],
        B: [[A, B, D]],
        C: [[C, D]],
        D: [[A, B, D], [C, D]],
    }
    assert order.get() == expected, f"Expected {expected}, got {order.get()}"


def test_total_order_full_str():
    A, B, C, D = "A", "B", "C", "D"
    order = TotalOrder[str]()
    order.add_rel(A, B)
    order.add_rel(B, D)
    order.add_rel(D, C)
    expected = {
        A: [[A, B, D, C]],
        B: [[A, B, D, C]],
        D: [[A, B, D, C]],
        C: [[A, B, D, C]],
    }
    assert order.get() == expected, f"Expected {expected}, got {order.get()}"


def test_total_order_isolated():
    A, B, C, D = "A", "B", "C", "D"
    order = TotalOrder[str]([A, B, C, D])
    order.add_rel(A, B)
    order.add_rel(B, D)
    expected = {
        A: [[A, B, D]],
        B: [[A, B, D]],
        C: [[C]],
        D: [[A, B, D]],
    }
    assert order.get() == expected, f"Expected {expected}, got {order.get()}"


def test_total_order_basic_named_obj():
    class obj:
        def __init__(self, name: str):
            self.name = name

        def __str__(self):
            return self.name

        def __repr__(self):
            return self.name

    A, B, C, D = obj("A"), obj("B"), obj("C"), obj("D")
    order = TotalOrder[obj]()
    order.add_rel(A, B)
    order.add_rel(B, D)
    order.add_rel(C, D)
    expected = {
        D: [[C, D], [A, B, D]],
        B: [[A, B, D]],
        C: [[C, D]],
        A: [[A, B, D]],
    }
    assert order.get() == expected, f"Expected {expected}, got {order.get()}"


def test_total_order_basic_anon_obj():
    A, B, C, D = times(4, object)
    order = TotalOrder[object]()
    order.add_rel(A, B)
    order.add_rel(B, D)
    order.add_rel(C, D)
    expected = {
        A: [[A, B, D]],
        B: [[A, B, D]],
        D: [[A, B, D], [C, D]],
        C: [[C, D]],
    }
    assert order.get() == expected, f"Expected {expected}, got {order.get()}"


def test_total_order_contradiction():
    A, B = "A", "B"
    order = TotalOrder[str]()
    order.add_rel(A, B)
    order.add_rel(B, A)
    expected = {
        A: [[A]],
        B: [[B]],
    }
    expected_cycles = {
        A: {A, B},
        B: {A, B},
    }
    assert order.get() == expected, f"Expected {expected}, got {order.get()}"
    assert (
        order.get_cycles() == expected_cycles
    ), f"Expected {expected_cycles}, got {order.get_cycles()}"

# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import time
import unittest
from itertools import combinations

import pytest

from faebryk.libs.util import (
    DAG,
    SharedReference,
    assert_once,
    complete_type_string,
    invert_dict,
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


def test_dag():
    dag = DAG[int]()
    dag.add_edge(1, 2)
    dag.add_edge(2, 3)

    assert dag.get(1).children == {2}
    assert dag.get(3).parents == {2}

    dag.add_edge(1, 3)
    assert dag.get(3).parents == {1, 2}
    assert dag.get(2).children == {3}
    assert dag.get(1).children == {2, 3}

    assert not dag.contains_cycles

    dag.add_edge(3, 1)
    assert dag.contains_cycles


def test_complete_type_string():
    a = {"a": 1, 5: object(), "c": {"a": 1}}
    assert complete_type_string(a) == "dict[str | int, int | object | dict[str, int]]"

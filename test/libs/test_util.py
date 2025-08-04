# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import time
import unittest
from itertools import combinations
from pathlib import Path

import pytest

from faebryk.libs.util import (
    DAG,
    SharedReference,
    assert_once,
    complete_type_string,
    invert_dict,
    list_match,
    once,
    path_replace,
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


def test_dag_topological_sort():
    # Test simple linear dependency
    dag = DAG[str]()
    dag.add_edge("A", "B")
    dag.add_edge("B", "C")

    sorted_nodes = dag.topologically_sorted()
    assert sorted_nodes == ["A", "B", "C"]

    # Test diamond dependency
    dag2 = DAG[str]()
    dag2.add_edge("A", "B")
    dag2.add_edge("A", "C")
    dag2.add_edge("B", "D")
    dag2.add_edge("C", "D")

    sorted_nodes2 = dag2.topologically_sorted()
    # A must come before B and C, B and C must come before D
    assert sorted_nodes2.index("A") < sorted_nodes2.index("B")
    assert sorted_nodes2.index("A") < sorted_nodes2.index("C")
    assert sorted_nodes2.index("B") < sorted_nodes2.index("D")
    assert sorted_nodes2.index("C") < sorted_nodes2.index("D")

    # Test with disconnected components
    dag3 = DAG[int]()
    dag3.add_edge(1, 2)
    dag3.add_edge(3, 4)
    dag3.add_edge(5, 6)

    sorted_nodes3 = dag3.topologically_sorted()
    # Each pair should maintain order
    assert sorted_nodes3.index(1) < sorted_nodes3.index(2)
    assert sorted_nodes3.index(3) < sorted_nodes3.index(4)
    assert sorted_nodes3.index(5) < sorted_nodes3.index(6)

    # Test cycle detection in topological sort
    dag_cycle = DAG[str]()
    dag_cycle.add_edge("A", "B")
    dag_cycle.add_edge("B", "C")
    dag_cycle.add_edge("C", "A")

    with pytest.raises(
        ValueError, match="Cannot topologically sort a graph with cycles"
    ):
        dag_cycle.topologically_sorted()

    # Test empty DAG
    dag_empty = DAG[int]()
    assert dag_empty.topologically_sorted() == []

    # Test single node (no edges)
    dag_single = DAG[str]()
    dag_single.add_or_get("A")
    assert dag_single.topologically_sorted() == ["A"]


def test_dag_get_subgraph():
    # Create a DAG with multiple connected components
    dag = DAG[str]()

    # Component 1: A -> B -> C -> D
    dag.add_edge("A", "B")
    dag.add_edge("B", "C")
    dag.add_edge("C", "D")

    # Component 2: E -> F -> G
    dag.add_edge("E", "F")
    dag.add_edge("F", "G")

    # Component 3: H -> I (disconnected)
    dag.add_edge("H", "I")

    # Test selecting node D includes all its dependencies
    subgraph1 = dag.get_subgraph(selector_func=lambda x: x == "D")
    sorted1 = subgraph1.topologically_sorted()
    assert sorted1 == ["A", "B", "C", "D"]

    # Test selecting multiple nodes
    subgraph3 = dag.get_subgraph(selector_func=lambda x: x in ["C", "G"])
    sorted3 = subgraph3.topologically_sorted()
    # Should have both chains up to C and G
    assert "A" in sorted3 and "B" in sorted3 and "C" in sorted3
    assert "E" in sorted3 and "F" in sorted3 and "G" in sorted3
    assert "D" not in sorted3  # D is a child of C, not a parent
    assert "H" not in sorted3 and "I" not in sorted3  # Disconnected component

    # Test empty selector
    subgraph4 = dag.get_subgraph(selector_func=lambda x: False)
    assert subgraph4.topologically_sorted() == []

    # Test selector that matches all
    subgraph5 = dag.get_subgraph(selector_func=lambda x: True)
    assert len(subgraph5.topologically_sorted()) == 9  # All nodes

    # Test non-direct dependencies are included
    # Create a longer chain: A -> B -> C -> D -> E
    dag_chain = DAG[str]()
    dag_chain.add_edge("A", "B")
    dag_chain.add_edge("B", "C")
    dag_chain.add_edge("C", "D")
    dag_chain.add_edge("D", "E")

    # Select E should include all ancestors A, B, C, D
    subgraph_chain = dag_chain.get_subgraph(selector_func=lambda x: x == "E")
    sorted_chain = subgraph_chain.topologically_sorted()
    assert sorted_chain == ["A", "B", "C", "D", "E"]

    # Test complex non-direct dependencies
    # Diamond with extension: A -> B -> D -> E
    #                         A -> C -> D -> E
    dag_complex = DAG[str]()
    dag_complex.add_edge("A", "B")
    dag_complex.add_edge("A", "C")
    dag_complex.add_edge("B", "D")
    dag_complex.add_edge("C", "D")
    dag_complex.add_edge("D", "E")

    # Select E should include all ancestors
    subgraph_complex = dag_complex.get_subgraph(selector_func=lambda x: x == "E")
    sorted_complex = subgraph_complex.topologically_sorted()
    assert "A" in sorted_complex
    assert "B" in sorted_complex
    assert "C" in sorted_complex
    assert "D" in sorted_complex
    assert "E" in sorted_complex
    assert len(sorted_complex) == 5


def test_complete_type_string():
    a = {"a": 1, 5: object(), "c": {"a": 1}}
    assert complete_type_string(a) == "dict[str | int, int | object | dict[str, int]]"


def test_ordered_set():
    from ordered_set import OrderedSet

    s = OrderedSet([1, 4, 2, 3, 4])
    assert s == {1: None, 4: None, 2: None, 3: None}
    assert s == {1, 4, 2, 3}
    assert list(s) == [1, 4, 2, 3]

    x = s | {5, 7, 6}
    assert x == {1, 4, 2, 3, 5, 6, 7}
    assert list(x) == [1, 4, 2, 3, 5, 6, 7]


@pytest.mark.parametrize(
    "base, match, expected",
    [
        ([1, 2, 3], [2, 3], [1]),
        ([1, 2, 3], [2, 3, 4], []),
        ([1, 2, 3], [1, 2, 3], [0]),
        ([1, 2, 3], [1, 2, 3, 4], []),
        ([1, 2, 3], [1, 2, 3, 4, 5], []),
    ],
)
def test_list_match(base, match, expected):
    assert list(list_match(base, match)) == expected


@pytest.mark.parametrize(
    "base, match, replacement, expected",
    [
        (Path("a/b/c"), Path("b"), Path("d"), Path("a/d/c")),
        (Path("a/b/c"), Path("b/c"), Path("d"), Path("a/d")),
        (Path("a/c/c"), Path("b/c"), Path("d"), Path("a/c/c")),
        (Path("a/c/c"), Path("c"), Path("d"), Path("a/d/d")),
        (Path("a/c/c/c/c"), Path("c/c"), Path("d"), Path("a/d/d")),
    ],
)
def test_path_replace(base, match, replacement, expected):
    assert path_replace(base, match, replacement) == expected

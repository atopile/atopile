# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import textwrap

import pytest

from faebryk.libs.util import md_list


def _fmt(s: str) -> str:
    return textwrap.dedent(s).strip()


@pytest.mark.parametrize(
    "obj,recursive,expected",
    [
        # Empty collections
        ([], False, "- *(empty)*"),
        ({}, False, "- *(empty)*"),
        # Simple list
        (
            [1, 2, 3],
            False,
            _fmt(
                """
                - 1
                - 2
                - 3
                """
            ),
        ),
        # Simple list with recursive flag
        (
            [1, 2, 3],
            True,
            _fmt(
                """
                - 1
                - 2
                - 3
                """
            ),
        ),
        # Simple dictionary
        (
            {"a": 1, "b": 2},
            False,
            _fmt(
                """
                - **a:** 1
                - **b:** 2
                """
            ),
        ),
        # Nested list, non-recursive
        (
            [1, [2, 3]],
            False,
            _fmt(
                """
                - 1
                - [2, 3]
                """
            ),
        ),
        # Nested list, recursive
        (
            [1, [2, 3]],
            True,
            _fmt(
                """
                - 1
                  - 2
                  - 3
                """
            ),
        ),
        # Nested dictionary, non-recursive
        (
            {"a": 1, "b": {"c": 2}},
            False,
            _fmt(
                """
                - **a:** 1
                - **b:** {'c': 2}
                """
            ),
        ),
        # Nested dictionary, recursive
        (
            {"a": 1, "b": {"c": 2}},
            True,
            _fmt(
                """
                - **a:** 1
                - **b:**
                  - **c:** 2
                """
            ),
        ),
        # Mixed nested structures, recursive
        (
            {"a": 1, "b": [2, 3]},
            True,
            _fmt(
                """
                - **a:** 1
                - **b:**
                  - 2
                  - 3
                """
            ),
        ),
        # Non-iterable object
        (123, False, "- 123"),
        # String
        (
            "abc",
            False,
            "- abc",
        ),
        # Deep nesting, recursive
        (
            [1, [2, [3, 4]]],
            True,
            _fmt(
                """
                - 1
                  - 2
                    - 3
                    - 4
                """
            ),
        ),
        # List of dicts of lists
        # TODO: currently not supported, but also not needed yet
        # (
        #     [{"a": [1, 2, 3], "b": [4, 5, 6]}, {"c": [7, 8, 9]}],
        #     False,
        #     _fmt(
        #         """
        #         - **a:**
        #           - 1
        #           - 2
        #           - 3
        #         - **b:**
        #           - 4
        #           - 5
        #           - 6
        #         - **c:**
        #           - 7
        #           - 8
        #           - 9
        #         """
        #     ),
        # ),
    ],
)
def test_md_list(obj, recursive, expected):
    assert md_list(obj, recursive=recursive) == expected

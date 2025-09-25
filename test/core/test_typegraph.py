from abc import abstractmethod
from typing import cast

import pytest

from faebryk.core.node import Node, _Node


def test_typegraph():
    class _trait1:
        pass

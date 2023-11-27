"""
Some attempt at distinct naming compared to itertools.
"""
from collections import deque
from typing import Callable, Iterable, Iterator, TypeVar

T = TypeVar("T")


def bfs(obj: T, child_getter: Callable[[T], Iterable[T]]) -> Iterator[T]:
    """Breadth-first search."""
    queue = deque([obj])

    while queue:
        obj = queue.popleft()
        yield obj

        for child in child_getter(obj):
            queue.append(child)


def ordered_unique(iterable: Iterable[T]) -> tuple[set[T], list[T]]:
    """Return a set and list (matching the order of the iterable) of unique items."""
    seen = set()
    unique_list = []

    for item in iterable:
        if item not in seen:
            seen.add(item)
            unique_list.append(item)

    return seen, unique_list

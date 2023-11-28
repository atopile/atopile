"""
Some attempt at distinct naming compared to itertools.
"""
from collections import deque
from typing import Callable, Iterable, Iterator, TypeVar

T = TypeVar("T")


def bfs(start: T, child_getter: Callable[[T], Iterable[T]]) -> Iterator[T]:
    """Breadth-first search."""
    queue = deque(child_getter(start))

    while queue:
        start = queue.popleft()
        yield start

        for child in child_getter(start):
            queue.append(child)


def unique_by_id(iterable: Iterable[T]) -> tuple[set[T], list[T]]:
    """Return a set of ids and a list of unique items. The list is in the same order as the iterable."""
    seen = set()
    unique_list = []

    for item in iterable:
        item_id = id(item)
        if item_id not in seen:
            seen.add(item_id)
            unique_list.append(item)

    return seen, unique_list

def unique_list(iterable: Iterable[T]) -> list[T]:
    """Return a list of unique items is in the same order as the iterable."""
    unique_items = []

    for item in iterable:
        if item not in unique_items:
            unique_items.append(item)

    return unique_items

import itertools
from collections import deque
from typing import Callable, Hashable, Iterable, Optional, TypeVar

import toolz
import toolz.curried

T = TypeVar("T")


def closest_common(
    things: Iterable[Iterable[T]],
    get_key: Callable[[T], Hashable] = toolz.identity,
    validate_common_root: bool = False,
) -> T:
    """Returns the closest common item between a set of iterables."""
    if not things:
        raise ValueError("No things given.")

    things = iter(things)

    # make a yardstick of the first iterable
    # this is a dict with the keys being the __key() of the items
    # and the values being the index of the item in the iterable
    index_and_item = itertools.tee(enumerate(next(things)))
    key_to_index_map = dict((get_key(item), i) for i, item in index_and_item[0])
    index_to_item_map = dict((i, item) for i, item in index_and_item[1])

    # set the index of the common item
    # this starts at 0 because if there's no other item we
    # just want to return the first item
    common_i = 0
    max_i = len(key_to_index_map) - 1

    def shortcut_if_common_is_already_root():
        if not validate_common_root:
            if common_i == max_i:
                # return early in the case we're already at the root
                return index_to_item_map[common_i]

    shortcut_if_common_is_already_root()

    for thing in things:
        for item in thing:
            key = get_key(item)
            if key in key_to_index_map:
                # if the item is in the yardstick, then we've found a common item
                # if the new common item is further than the old common item, we update it
                item_common_i = key_to_index_map[key]
                if item_common_i > common_i:
                    common_i = item_common_i
                    shortcut_if_common_is_already_root()
                break
        else:
            # if we didn't find a common item, then we raise an error
            raise ValueError("No common item found.")

    return index_to_item_map[common_i]


# NOTE:
# 1. For the dfs and bfs functions, I'm not convinced we want to yield the start first
#    I think it might be a bit annoying in some cases...
# 2. The get_children function is first for both functions so we can curry them, and so their
#    signatures are the same as map and filter


def dfs_postorder(
    get_children: Callable[[T], Iterable[T]],
    start: T,
) -> Iterable[T]:
    """Depth-first search, yielding the leaves first."""

    for child in get_children(start):
        yield from dfs_postorder(get_children, child)

    yield start


def bfs(
    get_children: Callable[[T], Iterable[T]],
    start: T,
) -> Iterable[T]:
    """Breadth-first search, first yielding the starting item."""
    yield start

    queue = deque(get_children(start))

    while queue:
        start = queue.popleft()
        yield start

        for child in get_children(start):
            queue.append(child)


def recurse(
    get_next: Callable[[T], Optional[T]],
    start: T,
) -> Iterable[T]:
    """Recursively yield items, optionally including the starting item and its children."""
    yield start
    next_item = get_next(start)
    if next_item is not None:
        yield from recurse(get_next, next_item)

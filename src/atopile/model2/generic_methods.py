import itertools
from typing import Any, Callable, Hashable, Iterable, TypeVar

import toolz.curried


T = TypeVar("T")


def match_values(__function: Callable[[T], bool]) -> Callable[[tuple[Hashable, T]], bool]:
    """Curried function that acts on the values of key-value pairs passed to it."""
    def __value_filter(item: tuple[Hashable, T]) -> bool:
        return __function(item[1])
    return __value_filter


def map_values(__function: Callable[[T], Any]) -> Callable[[tuple[Hashable, T]], tuple[Hashable, Any]]:
    """Curried function that maps the values of key-value pairs passed to it."""
    def __value_map(item: tuple[Hashable, T]) -> tuple[Hashable, Any]:
        return (item[0], __function(item[1]))
    return toolz.curried.map(__value_map)


def closest_common(
    things: Iterable[Iterable[T]],
    __key: Callable[[T], Hashable] = hash,
    validate_common_root: bool = False
) -> T:
    """Returns the closest common item between a set of iterables."""
    if not things:
        raise ValueError("No things given.")

    things = iter(things)

    # make a yardstick of the first iterable
    # this is a dict with the keys being the __key() of the items
    # and the values being the index of the item in the iterable
    index_and_item = itertools.tee(enumerate(next(things)))
    key_to_index_map = dict((__key(item), i) for i, item in index_and_item[0])
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
            key = __key(item)
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

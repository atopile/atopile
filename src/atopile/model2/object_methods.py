import functools
from collections import defaultdict
from typing import Callable, Iterable, Iterator, Optional

from atopile.model2 import datamodel as dm1
from atopile.model2.datamodel import Instance, Object
from atopile.model2.generic_methods import closest_common

def iter_supers(object: Object) -> Iterator[Object]:
    """Iterate over all the supers of an instance."""
    while object.supers_bfs is not None:
        object = object.supers_bfs[0]
        yield object


def lowest_common_super(objects: Iterable[Object], include_self: bool = True) -> Object:
    """
    Return the lowest common parent of a set of instances.
    """
    __iter_supers = functools.partial(iter_supers)
    return closest_common(map(__iter_supers, objects), __key=id)

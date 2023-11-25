"""
Find supers.
"""

from itertools import chain
from pathlib import Path
from typing import Mapping

from . import errors
from .datamodel import BUILTINS, Object
from .datatypes import Ref


def lookup_super(obj: Object, ref: Ref) -> Object:
    """
    Basic ref lookup for supers.
    """
    if ref.count() != 1:
        raise NotImplementedError

    scope = chain((obj,), obj.closure, (BUILTINS,))

    for candidate_obj in scope:
        if ref in candidate_obj.named_locals:
            return obj.named_locals[ref]

    raise KeyError(f"Name '{ref}' not found.")


def build(
    paths_to_objs: Mapping[Path, Object], error_handler: errors.ErrorHandler
) -> dict[str, Object]:
    """Build the model."""
    wendy = Wendy(error_handler)

    for obj in paths_to_objs.values():
        wendy.visit_object(obj)

    error_handler.do_raise_if_errors()

    return paths_to_objs


class Wendy:
    """Wendy's job is to walk through the tree and resolve objects supers tree into a linear lookup."""

    def __init__(self, error_handler: errors.ErrorHandler) -> None:
        self.error_handler = error_handler

    def visit_super(self, obj: Object) -> tuple[Object]:
        """
        DFS of supers.
        """
        if len(obj.supers_refs) > 0:
            raise NotImplementedError(
                "We can't currently support inheriting from more than one super."
            )
            # TODO: implement BFS of supers tree

        if len(obj.supers_refs) == 0:
            obj.supers_objs = ()
            return obj.supers_objs

        if obj.supers_objs is not None:
            return obj.supers_objs

        direct_supers = tuple(lookup_super(obj, ref) for ref in obj.supers_refs)
        obj.supers_objs = direct_supers + self.visit_super(direct_supers)
        return obj.supers_objs

    def visit_object(self, obj: Object) -> None:
        """
        Find all the supers of this object.
        Supers should be found as a depth-first search of the linked-list of supers on each object.
        """
        self.visit_super(obj)

        for next_obj in obj.locals_by_type[Object]:
            self.visit_object(next_obj)

"""
Find supers and replacements
"""

from itertools import chain
from pathlib import Path
from typing import Mapping

from atopile.iterutils import bfs, unique_list

from . import errors
from .datamodel import BUILTINS, Object, Replace
from .datatypes import Ref


def lookup_super(obj: Object, ref: Ref) -> Object:
    """
    Basic ref lookup for supers.

    Errors here are raised on the spot because they're not recoverable.
    """
    if len(ref) != 1:
        raise NotImplementedError("Multipart supers not implemented.")

    scope = chain((obj,), obj.closure)

    for candidate_obj in scope:
        if ref in candidate_obj.named_locals:
            return candidate_obj.named_locals[ref]

    if ref in BUILTINS:
        return BUILTINS[ref]

    raise KeyError(f"Name '{ref}' not found.")


def build(
    paths_to_objs: Mapping[Path, Object], error_handler: errors.ErrorHandler
) -> dict[str, Object]:
    """Build the model."""
    wendy = Wendy(error_handler)

    for obj in paths_to_objs.values():
        wendy.visit_object(obj)

    return paths_to_objs


class Wendy:
    """Wendy's job is to replace all the references to supers to actual objects."""

    def __init__(self, error_handler: errors.ErrorHandler) -> None:
        self.error_handler = error_handler

    def lookup_super(self, obj: Object, ref: Ref) -> Object:
        """Wrapper to catch errors"""
        try:
            return lookup_super(obj, ref)
        except KeyError as e:
            self.error_handler.handle(e)
            raise

    def visit_supers(self, obj: Object) -> tuple[Object]:
        """Visit and resolve supers in an object."""
        if obj.supers_objs is None:
            obj.supers_objs = tuple(self.lookup_super(obj, ref) for ref in obj.supers_refs)
        return obj.supers_objs

    def visit_object(self, obj: Object) -> tuple[Object]:
        """
        Visits an object and find its supers.
        It returns a tuple of the supers it finds its supers.
        """
        obj.supers_bfs = unique_list(bfs(obj, self.visit_supers))
        for _, obj in obj.locals_by_type[Object]:
            self.visit_object(obj)

    def visit_replacements(self, replace: Replace) -> None:
        """Visit and resolve replacements in an object."""
        replace.replacement_obj = self.lookup_super(replace.obj, replace.replacement_ref)

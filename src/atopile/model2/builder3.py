"""
Find supers.
"""

from itertools import chain

from . import errors
from .datamodel import Object, BUILTINS
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


class Wendy:
    """Wendy's job is to walk through the tree and resolve objects supers tree into a linear lookup."""
    def __init__(
        self, fail_fast: bool = False
    ) -> None:
        self.errors: list[Exception] = []
        self.fail_fast = fail_fast

    def handle_error(self, error: Exception) -> Exception:
        """
        Deal with an error, either by shoving it in the error list or raising it.
        """
        # This means that the automatic error handler won't show this function as the source of the error
        # Instead, it'll continue down the traceback to whatever called this function
        IGNORE_MY_EXCEPTIONS = (
            errors.IGNORE_MY_EXCEPTIONS
        )  # pylint: disable=unused-variable,invalid-name

        if self.fail_fast:
            raise error

        self.errors.append(error)
        return error

    def visit_super(self, obj: Object) -> tuple[Object]:
        """
        DFS of supers.
        """
        if len(obj.supers_refs) > 0:
            raise NotImplementedError("We can't currently support inheriting from more than one super.")
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

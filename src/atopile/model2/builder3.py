"""
Find supers and replacements
"""

from atopile.model2 import errors
from atopile.model2.datamodel import Object, Replace
from atopile.model2.object_methods import lookup_obj_in_closure


class Muck:
    """Wendy's job is to replace all the references to supers to actual objects."""

    def __init__(self, error_handler: errors.ErrorHandler) -> None:
        self.error_handler = error_handler

    def affix_supers(self, obj: Object) -> None:
        """Visit and resolve supers in an object."""
        try:
            # TODO: consider creating a ROOT_OBJECT sentinel or similar
            if obj.all_supers is None:
                assert obj.super_obj is None

                if obj.super_ref is None:
                    # this thing is a root object
                    # leave it be - it inherits from no one
                    obj.all_supers = ()
                    return

                obj.super_obj = lookup_obj_in_closure(obj, obj.super_ref)
                self.affix_supers(obj.super_obj)
                assert isinstance(obj.super_obj.all_supers, tuple)

                if self in obj.super_obj.all_supers:
                    raise errors.AtoCircularDependencyError.from_ctx(
                        f"Cyclical super found in {obj.super_obj}.", obj.src_ctx
                    )

                obj.all_supers = (obj.super_obj,) + obj.super_obj.all_supers
        except errors.AtoError as e:
            self.error_handler.handle(e)
            obj.errors.append(e)

    def visit_replace(self, rep: Replace) -> None:
        """Visit and resolve replacements in an object."""
        try:
            rep.replacement_obj = lookup_obj_in_closure(rep, rep.replacement_ref)
        except errors.AtoError as e:
            self.error_handler.handle(e)
            rep.errors.append(e)

    def visit_object(self, obj: Object) -> None:
        """
        Visits an object and find its supers.
        It returns a tuple of the supers it finds its supers.
        """
        self.affix_supers(obj)
        for obj in obj.objs.values():
            self.visit_object(obj)

        for replacement in obj.replacements:
            self.visit_replace(replacement)

"""
Find import references.
"""

from typing import Any, Mapping

from . import errors
from .datamodel import Import, Object
from .datatypes import Ref
from .parse_utils import get_src_info_from_ctx


def lookup_filename(cwd: str, filename: str) -> str:
    """Placeholder"""
    raise NotImplementedError


def lookup_ref(obj: Object, ref: Ref) -> Any:
    """
    Look up a ref as a path.

    Say you're looking for a.b.c

    Start by looking for a.b.c in the current object
    If that doesn't exist, look for a.b
    If that doesn't exist, look for a
    We start this way because imports can be multipart

    Once we find something, recurse to look for the remaining section of the reference, or return if we're done
    """
    if len(ref) == 0:
        return (obj,)

    if ref in obj.named_locals:
        return obj.named_locals[ref]

    for ref_len in range(len(ref)-1, 0, -1):
        ref_part = ref[:ref_len]
        if ref_part in obj.named_locals:
            remaining_ref = ref[ref_len:]
            next_obj = obj.named_locals[ref_part]
            if isinstance(next_obj, Object):
                return lookup_ref(next_obj, remaining_ref)

            if isinstance(next_obj, Import):
                raise TypeError("Importing from other files' import is not supported.")

            raise TypeError(f"Cannot look up {remaining_ref} in {next_obj}")

    raise KeyError(f"Name '{ref}' not found.")


class Lofty:
    """Lofty's job is to walk through the tree and resolve imports."""
    def __init__(
        self, paths_to_objs: Mapping[str, Object], fail_fast: bool = False
    ) -> None:
        self.paths_to_objs = paths_to_objs
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

    def visit_object(self, obj: Object) -> None:
        """Visit and resolve imports in an object."""
        for imp in obj.locals_by_type[Import]:
            assert isinstance(imp, Import)
            self.visit_import(imp)

        for next_obj in obj.locals_by_type[Object]:
            self.visit_object(next_obj)

    def visit_import(self, imp: Import) -> None:
        """Visit and resolve an import."""
        assert imp.src_ctx is not None
        cwd, _, _ = get_src_info_from_ctx(imp.src_ctx)
        foreign_filename = lookup_filename(cwd, imp.from_name)

        try:
            foreign_root = self.paths_to_objs[foreign_filename]
        except KeyError:
            self.handle_error(
                errors.AtoImportNotFoundError.from_ctx(
                    f"File '{foreign_filename}' not found.", imp.src_ctx
                )
            )
            return

        try:
            imp.what_obj = lookup_ref(foreign_root, imp.what_ref)
        except KeyError:
            self.handle_error(
                errors.AtoImportNotFoundError.from_ctx(
                    f"Name '{imp.what_ref}' not found in '{foreign_filename}'.",
                    imp.src_ctx,
                )
            )
            return
        except ValueError as ex:
            self.handle_error(errors.AtoError.from_ctx(ex.args[0], imp.src_ctx))
            return

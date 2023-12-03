"""
Find the objects imports reference, and link them up to the import objects.
"""

from itertools import chain
from pathlib import Path
from typing import Iterable, Mapping

from atopile.model2 import errors
from atopile.model2.datamodel import Import, Object
from atopile.model2.object_methods import lookup_obj_in_closure
from atopile.model2.parse_utils import get_src_info_from_ctx


class Lofty:
    """Lofty's job is to walk through the tree and resolve imports."""

    def __init__(
        self,
        paths_to_objs: Mapping[str, Object],
        error_handler: errors.ErrorHandler,
        search_paths: Iterable[Path]
    ) -> None:
        self.error_handler = error_handler
        self.paths_to_objs = paths_to_objs
        self.search_paths = search_paths

    def lookup_filename(self, cwd: str | Path, from_name: str) -> Path:
        """Look up a filename from a from_name."""
        # FIXME: we should probably only check the cwd is the part starts with ./
        cwd = Path(cwd)
        if cwd.is_file():
            cwd = cwd.parent

        search_paths: Iterable[Path] = chain((cwd,) + self.search_paths)
        for search_path in search_paths:
            candidate_path = search_path / from_name
            if candidate_path in self.paths_to_objs:
                return candidate_path

        raise FileNotFoundError

    def visit_object(self, obj: Object) -> None:
        """Visit and resolve imports in an object."""
        if obj.errors:
            # don't process dud objects
            return

        # sort out all the import statements in this object
        for imp in obj.imports:
            self.visit_import(imp)

        # ... then on to its locals!
        for next_obj in obj.objs:
            self.visit_object(next_obj)

    def visit_import(self, imp: Import) -> None:
        """Visit and resolve an import."""
        if imp.errors:
            # don't process dud imports
            return

        assert imp.src_ctx is not None
        cwd, _, _ = get_src_info_from_ctx(imp.src_ctx)

        try:  # TODO: there's probably a better way to rewrite this than as a nested try/except
            try:
                foreign_filename = self.lookup_filename(cwd, imp.from_name)
                foreign_root = self.paths_to_objs[foreign_filename]
                imp.what_obj = lookup_obj_in_closure(foreign_root, imp.what_ref)
            except KeyError as ex:
                raise errors.AtoImportNotFoundError.from_ctx(
                        f"Name '{imp.what_ref}' not found in '{foreign_filename}'.",
                        imp.src_ctx,
                    ) from ex
            except ValueError as ex:
                raise errors.AtoError.from_ctx(ex.args[0], imp.src_ctx)
            except FileNotFoundError as ex:
                raise errors.AtoImportNotFoundError.from_ctx(
                    f"File '{imp.from_name}' not found.", imp.src_ctx
                ) from ex
        except errors.AtoError as ex:
            imp.errors.append(ex)
            self.error_handler.handle(ex)

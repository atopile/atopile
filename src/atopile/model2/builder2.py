"""
Find import references.
"""

from itertools import chain
from pathlib import Path
from typing import Mapping, Iterable

from . import errors
from .datamodel import Import, Object
from .datatypes import Ref
from .parse_utils import get_src_info_from_ctx


def lookup_ref(obj: Object, ref: Ref) -> Object:
    """Basic ref lookup"""
    if len(ref) != 1:
        raise NotImplementedError

    if ref in obj.named_locals:
        return obj.named_locals[ref]

    raise KeyError(f"Name '{ref}' not found.")


def build(
    paths_to_objs: Mapping[Path, Object],
    error_handler: errors.ErrorHandler,
    search_paths: tuple[Path],
) -> Mapping[Path, Object]:
    """Build the model."""
    lofty = Lofty(paths_to_objs, error_handler, search_paths)

    for obj in paths_to_objs.values():
        lofty.visit_object(obj)

    return paths_to_objs


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
        cwd = Path(cwd)
        if cwd.is_file():
            cwd = cwd.parent

        for search_path in chain((cwd,) + self.search_paths):
            if (search_path / from_name) in self.paths_to_objs:
                return search_path / from_name

        raise FileNotFoundError

    def visit_object(self, obj: Object) -> None:
        """Visit and resolve imports in an object."""
        for _, imp in obj.locals_by_type[Import]:
            assert isinstance(imp, Import)
            self.visit_import(imp)

        for _, next_obj in obj.locals_by_type[Object]:
            self.visit_object(next_obj)

    def visit_import(self, imp: Import) -> None:
        """Visit and resolve an import."""
        assert imp.src_ctx is not None
        cwd, _, _ = get_src_info_from_ctx(imp.src_ctx)

        try:
            foreign_filename = self.lookup_filename(cwd, imp.from_name)
        except FileNotFoundError as ex:
            self.error_handler.handle(
                errors.AtoImportNotFoundError.from_ctx(
                    f"File '{imp.from_name}' not found.", imp.src_ctx
                ),
                ex
            )
            return

        foreign_root = self.paths_to_objs[foreign_filename]

        try:
            imp.what_obj = lookup_ref(foreign_root, imp.what_ref)
        except KeyError:
            self.error_handler.handle(
                errors.AtoImportNotFoundError.from_ctx(
                    f"Name '{imp.what_ref}' not found in '{foreign_filename}'.",
                    imp.src_ctx,
                )
            )
            return
        except ValueError as ex:
            self.error_handler.handle(errors.AtoError.from_ctx(ex.args[0], imp.src_ctx))
            return

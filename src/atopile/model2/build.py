"""
Lazily build flat models.
"""
from itertools import chain
from pathlib import Path
from typing import Iterable

from antlr4 import ParserRuleContext

from atopile.address import AddrStr
from atopile.lazy_map import LazyMap
from atopile.model2 import datamodel as dm
from atopile.model2.builder1 import Dizzy
from atopile.model2.builder2 import Lofty
from atopile.model2.builder3 import Muck
from atopile.model2.datamodel import Instance
from atopile.model2.datatypes import Ref
from atopile.model2.errors import ErrorHandler
from atopile.model2.flatten import build as flatten
from atopile.model2.parse import parse_file, parse_text_as_file


class Spud:
    """
    Spud is a very lazy model builder.

    TODO: Currently this is only lazy in the parsing of files, not compilation.
    """

    def __init__(self, error_handler: ErrorHandler, search_paths: Iterable[Path]) -> None:
        self.error_handler = error_handler

        # these paths must be clean and absolute, so that all the files' paths are unique and equally clean
        self.search_paths = map(lambda p: p.expanduser().resolve().absolute(), search_paths)

        known_files = chain.from_iterable(search_path.glob("**/*.ato") for search_path in self.search_paths)

        self.obj_map = LazyMap(self.build_file, known_files)

        self.dizzy = Dizzy(error_handler)
        self.lofty = Lofty(self.obj_map, error_handler, search_paths)
        self.muck = Muck(error_handler)

    def build_obj_from_ast(self, ast: ParserRuleContext) -> dm.Object:
        """Build an object from an AST."""
        obj = self.dizzy.build(ast)
        self.lofty.visit_object(obj)
        self.muck.visit_object(obj)

        return obj

    def build_file(self, file: Path) -> dm.Object:
        """Build an object."""
        ast = parse_file(file)
        return self.build_obj_from_ast(ast)

    def build_instance(self, addr: AddrStr) -> Instance:
        """Build an instance."""
        obj = self.obj_map[addr.file]

        obj_to_build = obj
        for ref_part in addr.node:
            obj_to_build = obj_to_build.named_locals[(ref_part,)]
        assert isinstance(obj_to_build, dm.Object)

        return flatten(obj_to_build)

    def add_obj_from_text(self, text: str, path: str | Path = "<empty>") -> dm.Object:
        """Build an object from text."""
        path = Path(path)
        ast = parse_text_as_file(text, path)
        obj = self.build_obj_from_ast(ast)
        self.obj_map[path] = obj

    def build_instance_from_text(self, text: str, ref: Ref, name = "<empty>") -> Instance:
        """Build an instance from text."""
        addr = AddrStr.from_parts(path=name, node=ref)
        self.add_obj_from_text(text, name)
        return self.build_instance(addr)

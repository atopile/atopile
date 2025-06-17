# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import indent

from atopile.front_end import _FeatureFlags

logger = logging.getLogger(__name__)


class _StrBuilder:
    def __init__(self) -> None:
        self.out = ""

    def append(self, content: str) -> None:
        self.out += content

    def append_line(self, line: str) -> None:
        self.append(line + "\n")

    def append_indented(self, content: str) -> None:
        self.append_line(indent(content, " " * 4))

    def spacer(self) -> None:
        if self.out:
            self.append_line("")

    def dump(self) -> str:
        return self.out


class AtoCodeGen:
    """
    This is the ghetto version of my other ato code generator that is not upstream.
    That one is a lot more complex, but in features and usage.
    So for the second we stick with this boi.
    """

    @dataclass(frozen=True, eq=True)
    class Import:
        name: str
        path: Path | None = None

    Experiment = _FeatureFlags.Feature

    @dataclass(kw_only=True)
    class Statement:
        _commented: bool = False

        def dump(self) -> str:
            out = _StrBuilder()
            if self._commented:
                out.append("#")
            out.append(self.dump_stmt())
            return out.dump()

        def dump_stmt(self) -> str: ...

        def comment_out(self):
            self._commented = True

    @dataclass
    class Trait(Statement):
        name: str
        args: dict[str, str] = field(default_factory=dict)
        constructor: str | None = None

        def dump_stmt(self) -> str:
            out = f"trait {self.name}"
            if self.constructor:
                out += f"::{self.constructor}"
            if self.args:
                out += f"<{', '.join(f'{k}="{v}"' for k, v in self.args.items())}>"
            return out

    @dataclass
    class PinDeclaration(Statement):
        name: str

        def dump_stmt(self) -> str:
            return f"pin {self.name}"

    @dataclass
    class Connect(Statement):
        class Connectable:
            def __init__(self, name: str, declare: str | None = None) -> None:
                self.name = name
                self.declare = declare

            def dump(self) -> str:
                out = _StrBuilder()
                if self.declare:
                    out.append(f"{self.declare} ")
                out.append(self.name)
                return out.dump()

        left: Connectable
        right: Connectable

        def dump_stmt(self) -> str:
            return f"{self.left.dump()} ~ {self.right.dump()}"

    class Spacer(Statement):
        def dump(self) -> str:
            return ""

    @dataclass
    class Comment(Statement):
        text: str

        def dump_stmt(self) -> str:
            return f"# {self.text}"

        @classmethod
        def from_lines(cls, *lines: str) -> list["AtoCodeGen.Comment"]:
            return [cls(line) for line in lines]

    @dataclass
    class ComponentFile:
        identifier: str | None = None
        imports: set["AtoCodeGen.Import"] = field(default_factory=set)
        experiments: set["AtoCodeGen.Experiment"] = field(default_factory=set)
        stmts: list["AtoCodeGen.Statement"] = field(default_factory=list)
        docstring: str | None = None

        def dump(self) -> str:
            if self.identifier is None:
                raise ValueError("identifier is required")

            out = _StrBuilder()

            for exp in self.experiments:
                out.append_line(f'#pragma experiment("{exp.value}")')

            for imp in sorted(self.imports, key=lambda x: x.name):
                if imp.path:
                    out.append(f"from {imp.path} ")
                out.append_line(f"import {imp.name}")

            out.spacer()

            out.append_line(f"component {self.identifier}:")
            if self.docstring:
                out.append_indented(f'"""{self.docstring}"""')
                out.spacer()

            for stmt in self.stmts:
                out.append_indented(stmt.dump())

            return out.dump()

        def add_stmt(self, stmt: "AtoCodeGen.Statement") -> None:
            self.stmts.append(stmt)

        def add_comments(self, *comments: str, use_spacer: bool = False) -> None:
            self.add_stmts(
                *AtoCodeGen.Comment.from_lines(*comments), use_spacer=use_spacer
            )

        def add_trait(
            self,
            name: str,
            constructor: str | None = None,
            auto_import: bool = True,
            **args: str | None,
        ) -> "AtoCodeGen.Trait":
            self.enable_experiment(AtoCodeGen.Experiment.TRAITS)

            if auto_import:
                self.imports.add(AtoCodeGen.Import(name))

            trait = AtoCodeGen.Trait(
                name,
                args={k: v for k, v in args.items() if v is not None},
                constructor=constructor,
            )
            self.add_stmt(trait)
            return trait

        def enable_experiment(self, experiment: "AtoCodeGen.Experiment") -> None:
            self.experiments.add(experiment)

        def add_stmts(
            self, *stmts: "AtoCodeGen.Statement", use_spacer: bool = True
        ) -> None:
            if use_spacer:
                self.add_stmt(AtoCodeGen.Spacer())
            for stmt in stmts:
                self.add_stmt(stmt)

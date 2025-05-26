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

    @dataclass
    class Import:
        name: str
        path: Path | None = None

    Experiment = _FeatureFlags.Feature

    class Statement:
        def dump(self) -> str: ...

    @dataclass
    class Trait(Statement):
        name: str
        args: dict[str, str] = field(default_factory=dict)

        def dump(self) -> str:
            out = f"trait {self.name}"
            if self.args:
                out += f"<{', '.join(f'{k}="{v}"' for k, v in self.args.items())}>"
            return out

    class Spacer(Statement):
        def dump(self) -> str:
            return ""

    @dataclass
    class Comment(Statement):
        text: str

        def dump(self) -> str:
            return f"# {self.text}"

        @classmethod
        def from_lines(cls, *lines: str) -> list["AtoCodeGen.Comment"]:
            return [cls(line) for line in lines]

    @dataclass
    class ComponentFile:
        identifier: str | None = None
        imports: list["AtoCodeGen.Import"] = field(default_factory=list)
        experiments: set["AtoCodeGen.Experiment"] = field(default_factory=set)
        stmts: list["AtoCodeGen.Statement"] = field(default_factory=list)

        def dump(self) -> str:
            if self.identifier is None:
                raise ValueError("identifier is required")

            out = _StrBuilder()

            for exp in self.experiments:
                out.append_line(f'#pragma experiment("{exp.value}")')

            for imp in self.imports:
                if imp.path:
                    out.append(f"from {imp.path} ")
                out.append_line(f"import {imp.name}")

            out.spacer()

            out.append_line(f"component {self.identifier}:")

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
            args: dict[str, str] | None = None,
            auto_import: bool = True,
        ) -> "AtoCodeGen.Trait":
            self.enable_experiment(AtoCodeGen.Experiment.TRAITS)

            if auto_import:
                self.imports.append(AtoCodeGen.Import(name))

            trait = AtoCodeGen.Trait(name, args or {})
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

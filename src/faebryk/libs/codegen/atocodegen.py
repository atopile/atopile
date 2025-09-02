# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import indent
from typing import ClassVar, Literal

import faebryk.library._F as F
from atopile.front_end import _FeatureFlags
from faebryk.libs.codegen.pycodegen import sanitize_name  # noqa: F401

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


def _quote(s: str | Path) -> str:
    # TODO: escape quotes in string
    return f'"{s}"'


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

        def dump(self) -> str:
            out = _StrBuilder()
            if self.path:
                out.append(f"from {_quote(self.path)} ")
            out.append(f"import {self.name}")
            return out.dump()

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
    class FieldDeclaration(Statement):
        name: str
        type: str

        def dump_stmt(self) -> str:
            return f"{self.name}: {self.type}"

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
    class New(Statement):
        type: str
        kwargs: dict[str, str]

        def dump_stmt(self) -> str:
            template = ""
            if self.kwargs:
                template_args = ", ".join(
                    f"{k}={_quote(v)}" for k, v in self.kwargs.items()
                )
                template = f"<{template_args}>"
            return f"new {self.type}{template}"

    @dataclass
    class Assignment(Statement):
        address: str
        value: "AtoCodeGen.Statement | str"
        attribute: str | None = None

        def dump_stmt(self) -> str:
            left = (
                f"{self.address}.{self.attribute}" if self.attribute else self.address
            )

            value_str = (
                self.value.dump_stmt()
                if isinstance(self.value, AtoCodeGen.Statement)
                else self.value
            )

            return f"{left} = {value_str}"

    @dataclass
    class Retype(Statement):
        address: str
        type: str

        def dump_stmt(self) -> str:
            return f"{self.address} -> {self.type}"

    @dataclass
    class Block:
        name: str
        stmts: list["AtoCodeGen.Statement"] = field(default_factory=list)
        docstring: str | None = None
        type: Literal["module", "component"] = "module"

        def add_stmt(self, stmt: "AtoCodeGen.Statement") -> None:
            self.stmts.append(stmt)

        def add_stmts(
            self, *stmts: "AtoCodeGen.Statement", use_spacer: bool = True
        ) -> None:
            if use_spacer:
                self.add_stmt(AtoCodeGen.Spacer())
            for stmt in stmts:
                self.add_stmt(stmt)

        def add_comments(self, *comments: str, use_spacer: bool = False) -> None:
            self.add_stmts(
                *AtoCodeGen.Comment.from_lines(*comments), use_spacer=use_spacer
            )

        def dump(self) -> str:
            out = _StrBuilder()
            out.append_line(f"{self.type} {self.name}:")
            if self.docstring:
                out.append_indented(f'"""{self.docstring}"""')
                out.spacer()

            if self.stmts:
                for stmt in self.stmts:
                    out.append_indented(stmt.dump())
            else:
                out.append_indented("pass")

            return out.dump()

    @dataclass
    class Module(Block):
        type: Literal["module", "component"] = "module"

    @dataclass
    class Component(Block):
        type: Literal["module", "component"] = "component"

    @dataclass
    class File:
        experiments: set["AtoCodeGen.Experiment"] = field(default_factory=set)
        imports: set["AtoCodeGen.Import"] = field(default_factory=set)
        blocks: list["AtoCodeGen.Block"] = field(default_factory=list)

        # def add_trait(
        #     self,
        #     name: str,
        #     constructor: str | None = None,
        #     auto_import: bool = True,
        #     **args: str | None,
        # ) -> "AtoCodeGen.Trait":
        #     self.enable_experiment(AtoCodeGen.Experiment.TRAITS)

        #     if auto_import:
        #         self.imports.add(AtoCodeGen.Import(name))

        #     trait = AtoCodeGen.Trait(
        #         name=name,
        #         args={k: v for k, v in args.items() if v is not None},
        #         constructor=constructor,
        #     )
        #     self.add_stmt(trait)
        #     return trait

        def enable_experiment(self, experiment: "AtoCodeGen.Experiment") -> None:
            self.experiments.add(experiment)

        def add_block(self, block: "AtoCodeGen.Block") -> None:
            self.blocks.append(block)

        def add_component(self, component: "AtoCodeGen.Component") -> None:
            self.blocks.append(component)

        def add_module(self, module: "AtoCodeGen.Module") -> None:
            self.blocks.append(module)

        def add_import(self, to_import: str, from_path: Path | None = None) -> None:
            self.imports.add(AtoCodeGen.Import(to_import, from_path))

    @dataclass
    class ComponentFile(File):
        identifier: str | None = None

        def __post_init__(self) -> None:
            if self.identifier is None:
                raise ValueError("identifier is required")

            self.add_block(AtoCodeGen.Component(name=self.identifier))

        def add_comments(self, *comments: str, use_spacer: bool = False) -> None:
            self.blocks[0].add_comments(*comments, use_spacer=use_spacer)

        def add_trait(
            self, name: str, constructor: str | None = None, **kwargs: str | None
        ) -> None:
            self.blocks[0].add_stmt(
                AtoCodeGen.Trait(
                    name=name,
                    constructor=constructor,
                    args={k: v for k, v in kwargs.items() if v is not None},
                )
            )

        def add_pin(self, pin: "AtoCodeGen.PinDeclaration") -> None:
            self.blocks[0].add_stmt(pin)

        def add_connect(self, connect: "AtoCodeGen.Connect") -> None:
            self.blocks[0].add_stmt(connect)

        def dump(self) -> str:
            out = _StrBuilder()

            for exp in self.experiments:
                out.append_line(f'#pragma experiment("{exp.value}")')

            for imp in sorted(self.imports, key=lambda x: x.name):
                out.append(imp.dump())

            out.spacer()

            for block in self.blocks:
                out.append(block.dump())

            return out.dump()

    @dataclass
    class PicksFile(File):
        PICKS_MODULE_NAME: ClassVar[str] = "PICKS"
        picks: list["AtoCodeGen.Assignment"] = field(default_factory=list)
        entry: str | None = None
        file: Path | None = None

        def __post_init__(self) -> None:
            self.experiments.add(AtoCodeGen.Experiment.TRAITS)
            self.experiments.add(AtoCodeGen.Experiment.MODULE_TEMPLATING)
            self.add_import(F.has_part_picked.__name__)
            self.add_import(F.has_part_picked_by_supplier.__name__)

        def add_pick(self, pick: "AtoCodeGen.Assignment") -> None:
            self.picks.append(pick)

        def dump(self) -> str:
            out = _StrBuilder()

            assert self.file is not None, "file is required"
            assert self.entry is not None, "entry is required"

            self.add_import(self.entry, self.file)

            picks_module = AtoCodeGen.Module(
                name=self.PICKS_MODULE_NAME,
                stmts=[
                    AtoCodeGen.Assignment(
                        address="app", value=AtoCodeGen.New(type=self.entry, kwargs={})
                    ),
                    AtoCodeGen.Spacer(),
                ],
            )

            for exp in self.experiments:
                out.append_line(f'#pragma experiment("{exp.value}")')

            out.spacer()

            for imp in sorted(self.imports, key=lambda x: x.name):
                out.append_line(imp.dump())

            out.spacer()

            for block in self.blocks:
                out.append_line(block.dump())

            for pick in self.picks:
                picks_module.add_stmt(pick)

            out.append(picks_module.dump())

            return out.dump()

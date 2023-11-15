"""
This datamodel represents the code in a clean, simple and traversable way, but doesn't resolve names of things
In building this datamodel, we check for name collisions, but we don't resolve them yet.
"""

import enum
import itertools
import logging
import typing
from typing import Any, Iterable, Optional

from attrs import define, field

from atopile.model2 import errors, types
from atopile.model2.parse import ParserRuleContext
from atopile.parser.AtopileParser import AtopileParser as ap
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


Ref = tuple[str | int]


@define
class Base:
    # this is a str rather than a path because it might just be virtual
    src_path: Optional[str] = field(default=None, kw_only=True, eq=False)
    src_ctx: Optional[ParserRuleContext] = field(default=None, kw_only=True, eq=False)


@define
class Link(Base):
    source: Ref
    target: Ref


@define
class Replace(Base):
    original: Ref
    replacement: Ref


@define
class Import(Base):
    what: Ref
    from_: str


@define
class Object(Base):
    supers: tuple[Ref] = field(factory=tuple)
    locals_: tuple[tuple[Optional[Ref], Any]] = field(factory=tuple)


MODULE = (("module",),)
COMPONENT = MODULE + (("component",),)

PIN = (("pin",),)
SIGNAL = (("signal",),)
INTERFACE = (("interface",),)

## Usage Example

# file = Object(class_=MODULE, supers=[], locals_={})

# Resistor = Object(
#     supers=[COMPONENT],
#     locals_={
#         1: Object(class_=PIN),
#         2: Object(class_=PIN),
#         "test": 1,
#     },
# )

# in this data model we make everything by reference
# vdiv_named_link = Link(source=("r_top", 1), target=("top",))
# VDiv = Object(
#     supers=[MODULE],
#     locals_={
#         "top": Object(class_=SIGNAL),
#         "out": Object(class_=SIGNAL),
#         "bottom": Object(class_=SIGNAL),
#         "r_top": Object(class_=("Resistor",)),
#         "r_bottom": Object(class_=("Resistor",)),
#         "top_link": vdiv_named_link,
#         ("r_top", "test"): 2,
#         (None, Link(source=("r_top", 2), target=("out",))),
#         (None, Link(source=("r_bottom", 1), target=("out",))),
#         (None, Link(source=("r_bottom", 2), target=("bottom",))),
#     },
# )


# Test = Object(
#     supers=[MODULE],
#     anon=[Replace(original=("vdiv", "r_top"), replacement=("Resistor2",))],
#     locals_={
#         "vdiv": Object(class_=("VDiv",)),
#     },
# )

## Return struct


class Type(enum.Enum):
    LINK = enum.auto()
    OBJECT = enum.auto()
    REPLACE = enum.auto()


## Builder


class _Sentinel(enum.Enum):
    NOTHING = enum.auto()


NOTHING = _Sentinel.NOTHING


class Dizzy(AtopileParserVisitor):
    """
    Dizzy is responsible for mixing cement, sand, aggregate, and water to create concrete.
    Ref.: https://www.youtube.com/watch?v=drBge9JyloA
    """

    def __init__(
        self,
        name: str,
    ) -> None:
        # TODO: get this outta here
        self.src_path = name
        super().__init__()

    def defaultResult(self):
        return NOTHING

    def visit_iterable_helper(
        self, children: Iterable
    ) -> tuple[tuple[Optional[Ref], Any]]:
        results = tuple(self.visit(child) for child in children)
        return tuple(itertools.chain(*filter(lambda x: x is not NOTHING, results)))

    def visitSimple_stmt(self, ctx: ap.Simple_stmtContext) -> _Sentinel | tuple:
        """
        This is practically here as a development shim to assert the result is as intended
        """
        result = self.visitChildren(ctx)
        if result is not NOTHING:
            assert isinstance(result, tuple)
            if len(result) > 0:
                assert isinstance(result[0], tuple)
                assert len(result[0]) == 2
        return result

    def visitStmt(self, ctx: ap.StmtContext) -> tuple[tuple[Optional[Ref], Any]]:
        """
        Ensure consistency of return type
        """
        if ctx.simple_stmts():
            value = self.visitSimple_stmts(ctx.simple_stmts())
        elif ctx.compound_stmt():
            value = (self.visit(ctx.compound_stmt()),)
        else:
            raise errors.AtoError("Unexpected statement type")
        return value

    def visitSimple_stmts(
        self, ctx: ap.Simple_stmtsContext
    ) -> tuple[tuple[Optional[Ref], Any]]:
        return self.visit_iterable_helper(ctx.simple_stmt())

    def visitTotally_an_integer(self, ctx: ap.Totally_an_integerContext) -> int:
        text = ctx.getText()
        try:
            return int(text)
        except ValueError:
            raise errors.AtoTypeError(f"Expected an integer, but got {text}")

    def visitFile_input(self, ctx: ap.File_inputContext) -> Object:
        return Object(
            src_ctx=ctx,
            src_path=self.src_path,
            supers=MODULE,
            locals_=self.visit_iterable_helper(ctx.stmt()),
        )

    def visitBlocktype(self, ctx: ap.BlocktypeContext) -> tuple[Ref]:
        block_type_name = ctx.getText()
        match block_type_name:
            case "module":
                return MODULE
            case "component":
                return COMPONENT
            case "interface":
                return INTERFACE
            case _:
                raise errors.AtoError(f"Unknown block type '{block_type_name}'")

    def visit_ref_helper(
        self,
        ctx: ap.NameContext
        | ap.AttrContext
        | ap.Name_or_attrContext
        | ap.Totally_an_integerContext,
    ) -> Ref:
        """
        Visit any referencey thing and ensure it's returned as a reference
        """
        if isinstance(ctx, (ap.NameContext, ap.Totally_an_integerContext, ap.Numerical_pin_refContext)):
            return (self.visit(ctx),)
        if isinstance(ctx, (ap.AttrContext, ap.Name_or_attrContext)):
            return self.visit(ctx)
        raise errors.AtoError(f"Unknown reference type: {type(ctx)}")

    def visitName(self, ctx: ap.NameContext) -> str | int:
        """
        If this is an int, convert it to one (for pins), else return the name as a string.
        """
        try:
            return int(ctx.getText())
        except ValueError:
            return ctx.getText()

    def visitAttr(self, ctx: ap.AttrContext) -> tuple[str]:
        return tuple(self.visitName(name) for name in ctx.name())  # Comprehension

    # TODO: reimplement that function
    def visitName_or_attr(self, ctx: ap.Name_or_attrContext) -> tuple[str]:
        if ctx.name():
            # TODO: I believe this should return a tuple
            return (self.visitName(ctx.name()),)
        elif ctx.attr():
            return self.visitAttr(ctx.attr())

        raise errors.AtoError("Expected a name or attribute")

    def visitBlock(self, ctx) -> tuple[tuple[Optional[Ref], Any]]:
        if ctx.simple_stmts():
            return self.visitSimple_stmts(ctx.simple_stmts())
        elif ctx.stmt():
            return self.visit_iterable_helper(ctx.stmt())
        else:
            raise errors.AtoError("Unexpected block type")

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> tuple[Optional[Ref], Object]:
        block_returns = self.visitBlock(ctx.block())
        # blockdef: blocktype name ('from' name_or_attr)? ':' block;
        # block: block: simple_stmts | NEWLINE INDENT stmt+ DEDENT;

        if ctx.FROM():
            if not ctx.name_or_attr():
                raise errors.AtoError("Expected a name or attribute after 'from'")
            block_supers = (self.visit_ref_helper(ctx.name_or_attr()),)
        else:
            block_supers = self.visitBlocktype(ctx.blocktype())

        return (
            self.visit_ref_helper(ctx.name()),
            Object(
                src_path=self.src_path,
                src_ctx=ctx,
                supers=block_supers,
                locals_=block_returns,
            ),
        )

    # TODO: reimplement
    def visitPindef_stmt(
        self, ctx: ap.Pindef_stmtContext
    ) -> tuple[tuple[Optional[Ref], Object]]:
        ref = self.visit_ref_helper(ctx.totally_an_integer() or ctx.name())

        # TODO: provide context of where this error was found within the file
        if not ref:
            raise errors.AtoError("Pins must have a name")
        # TODO: reimplement this error handling at the above level
        created_pin = Object(
            src_path=self.src_path,
            src_ctx=ctx,
            supers=PIN,
        )

        return ((ref, created_pin),)

    # TODO: reimplement
    def visitSignaldef_stmt(
        self, ctx: ap.Signaldef_stmtContext
    ) -> tuple[tuple[Optional[Ref], Object]]:
        name = self.visit_ref_helper(ctx.name())

        # TODO: provide context of where this error was found within the file
        if not name:
            raise errors.AtoError("Signals must have a name")

        created_signal = Object(
            src_path=self.src_path,
            src_ctx=ctx,
            supers=(SIGNAL),
        )
        # TODO: reimplement this error handling at the above level
        # if name in self.scope:
        #     raise errors.AtoNameConflictError(
        #         f"Cannot redefine '{name}' in the same scope"
        #     )
        return ((name, created_signal),)

    # Import statements have no ref
    def visitImport_stmt(self, ctx: ap.Import_stmtContext) -> tuple[tuple[Ref, Import]]:
        from_file: str = self.visitString(ctx.string())
        imported_element = self.visit_ref_helper(ctx.name_or_attr())

        if not from_file:
            raise errors.AtoError("Expected a 'from <file-path>' after 'import'")
        if not imported_element:
            raise errors.AtoError(
                "Expected a name or attribute to import after 'import'"
            )

        if imported_element == "*":
            # import everything
            raise NotImplementedError("import *")

        return (
            (
                imported_element,
                Import(
                    src_path=self.src_path,
                    src_ctx=ctx,
                    what=imported_element,
                    from_=from_file,
                ),
            ),
        )

    # if a signal or a pin def statement are executed during a connection, it is returned as well
    def visitConnectable(
        self, ctx: ap.ConnectableContext
    ) -> tuple[Ref, Optional[tuple[Optional[Ref], Object]]]:
        if ctx.name_or_attr():
            # Returns a tuple
            return self.visit_ref_helper(ctx.name_or_attr()), None
        elif ctx.numerical_pin_ref():
            return self.visit_ref_helper(ctx.numerical_pin_ref()), None
        elif ctx.pindef_stmt() or ctx.signaldef_stmt():
            connectable = self.visitChildren(ctx)[0]
            # return the object's ref and the created object itself
            return connectable[0], connectable
        else:
            raise ValueError("Unexpected context in visitConnectable")

    def visitConnect_stmt(
        self, ctx: ap.Connect_stmtContext
    ) -> tuple[tuple[Optional[Ref], Object]]:
        """
        Connect interfaces together
        """
        source_name, source = self.visitConnectable(ctx.connectable(0))
        target_name, target = self.visitConnectable(ctx.connectable(1))

        returns = [
            (
                None,
                Link(source_name, target_name),
            )
        ]

        # If the connect statement is also used to instantiate an element, add it to the return tuple
        if source:
            returns.append(source)

        if target:
            returns.append(target)

        # TODO: not sure that's the cleanest way to return a tuple
        return tuple(returns)

    def visitWith_stmt(self, ctx: ap.With_stmtContext) -> tuple[Optional[Ref], Object]:
        """
        # TODO: remove
        FIXME: I'm not entirely sure what this is for
        Remove it soon if we don't figure it out
        """
        raise NotImplementedError

    def visitNew_stmt(self, ctx: ap.New_stmtContext) -> Object:
        new_object_name = self.visit_ref_helper(ctx.name_or_attr())

        return Object(
            src_path=self.src_path, src_ctx=ctx, supers=new_object_name, locals_=()
        )

    def visitString(self, ctx: ap.StringContext) -> str:
        return ctx.getText().strip("\"'")

    def visitBoolean_(self, ctx: ap.Boolean_Context) -> bool:
        return ctx.getText().lower() == "true"

    def visitAssignable(
        self, ctx: ap.AssignableContext
    ) -> tuple[Optional[Ref], Object] | int | float | str:
        if ctx.name_or_attr():
            scope, name = self.visitName_or_attr(ctx.name_or_attr())
            return scope[name]

        if ctx.new_stmt():
            return self.visit(ctx.new_stmt())

        if ctx.NUMBER():
            value = float(ctx.NUMBER().getText())
            return int(value) if value.is_integer() else value

        if ctx.string():
            return self.visitString(ctx)

        if ctx.boolean_():
            return self.visitBoolean_(ctx.boolean_())

    def visitAssign_stmt(self, ctx: ap.Assign_stmtContext) -> tuple[tuple[Ref, str]]:
        assigned_value_name = self.visitName_or_attr(ctx.name_or_attr())
        assigned_value = self.visitAssignable(ctx.assignable())

        return ((assigned_value_name, assigned_value),)

    def visitRetype_stmt(
        self, ctx: ap.Retype_stmtContext
    ) -> tuple[tuple[Optional[Ref], Replace]]:
        """
        This statement type will replace an existing block with a new one of a subclassed type

        Since there's no way to delete elements, we can be sure that the subclass is
        a superset of the superclass (confusing linguistically, makes sense logically)
        """
        original_name = self.visit_ref_helper(ctx.name_or_attr(0))
        replaced_name = self.visit_ref_helper(ctx.name_or_attr(1))
        return (
            (
                None,
                Replace(
                    src_path=self.src_path,
                    src_ctx=ctx,
                    original=original_name,
                    replacement=replaced_name,
                ),
            ),
        )

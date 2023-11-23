"""
This datamodel represents the code in a clean, simple and traversable way, but doesn't resolve names of things
In building this datamodel, we check for name collisions, but we don't resolve them yet.
"""
import enum
import itertools
import logging
from typing import Any, Iterable, Optional, Mapping

from antlr4 import ParserRuleContext
from attrs import define, field, resolve_types

from atopile.model2 import errors
from atopile.parser.AtopileParser import AtopileParser as ap
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


Ref = tuple[str]


class OptionallyNamedItem(tuple[Ref, Any]):
    """A class representing anf optionally-named thing."""
    @property
    def ref(self) -> Ref:
        return self[0]

    @property
    def value(self) -> Any:
        return self[1]


class OptionallyNamedItems(tuple[OptionallyNamedItem]):
    """A class representing a set of optionally-named things."""
    def get_named_items(self) -> Mapping[str, Any]:
        """Return all the named items in this set, ignoring the unnamed ones."""
        return dict(filter(lambda x: x.ref is not None, self))

    def get_unnamed_items(self) -> Iterable[Any]:
        """Return an interable of all the unnamed items in this set."""
        return map(lambda x: x.value, filter(lambda x: x.ref is None, self))


@define
class Base:
    """Base class for all objects in the datamodel."""
    # this is a str rather than a path because it might just be virtual
    src_ctx: ParserRuleContext = field(kw_only=True, eq=False)


@define
class Link(Base):
    """Represent a connection between two connectable things."""
    source: Ref
    target: Ref


@define
class Replace(Base):
    """Represent a replacement of one object with another."""
    original: Ref
    replacement: Ref


@define
class Import(Base):
    """Represent an import statement."""
    what: Ref
    from_: str


@define
class Object(Base):
    """Represent a container class."""
    closure: tuple["Object"]

    # everything else needs defaults because of circular references
    supers: Optional[tuple[Ref]] = None
    locals_: Optional[OptionallyNamedItems] = None

    # generated from the locals_
    name_bindings: dict[str, Any] = None


resolve_types(Object)  # resolve in post is required because of the circular reference


# these are the build-in superclasses that have special meaning to the compiler
MODULE = (("module",),)
COMPONENT = MODULE + (("component",),)

PIN = (("pin",),)
SIGNAL = (("signal",),)
INTERFACE = (("interface",),)


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
        src_path: str,
    ) -> None:
        self.src_path = src_path
        super().__init__()

    def defaultResult(self):
        return NOTHING

    def visit_iterable_helper(
        self, children: Iterable
    ) -> OptionallyNamedItems:
        """
        Visit multiple children and return a tuple of their results,
        discard any results that are NOTHING and flattening the children's results.
        It is assumed the children are returning their own OptionallyNamedItems.
        """
        results = (self.visit(child) for child in children)
        return OptionallyNamedItems(itertools.chain(*filter(lambda x: x is not NOTHING, results)))

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

    def visitStmt(self, ctx: ap.StmtContext) -> OptionallyNamedItems:
        """
        Ensure consistency of return type
        """
        if ctx.simple_stmts():
            value = self.visitSimple_stmts(ctx.simple_stmts())
        elif ctx.compound_stmt():
            value = OptionallyNamedItems(self.visit(ctx.compound_stmt()),)
        else:
            raise errors.AtoError("Unexpected statement type")
        return value

    def visitSimple_stmts(
        self, ctx: ap.Simple_stmtsContext
    ) -> OptionallyNamedItems:
        return self.visit_iterable_helper(ctx.simple_stmt())

    def visitTotally_an_integer(self, ctx: ap.Totally_an_integerContext) -> str:
        text = ctx.getText()
        try:
            int(text)
        except ValueError as ex:
            raise errors.AtoTypeError(f"Expected an integer, but got {text}") from ex

        return text

    def visitFile_input(self, ctx: ap.File_inputContext) -> Object:
        obj = Object(
            closure=(),
            src_ctx=ctx,
            supers=MODULE,
        )
        locals_ = self.visit_iterable_helper(ctx.stmt())
        obj.locals_ = locals_
        obj.name_bindings = locals_.get_named_items()
        return obj

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
        if isinstance(
            ctx,
            (ap.NameContext, ap.Totally_an_integerContext, ap.Numerical_pin_refContext),
        ):
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

    def visitAttr(self, ctx: ap.AttrContext) -> Ref:
        return tuple(self.visitName(name) for name in ctx.name())  # Comprehension

    def visitName_or_attr(self, ctx: ap.Name_or_attrContext) -> Ref:
        if ctx.name():
            return (self.visitName(ctx.name()),)
        elif ctx.attr():
            return self.visitAttr(ctx.attr())

        raise errors.AtoError("Expected a name or attribute")

    def visitBlock(self, ctx) -> OptionallyNamedItems:
        if ctx.simple_stmts():
            return self.visitSimple_stmts(ctx.simple_stmts())
        elif ctx.stmt():
            return self.visit_iterable_helper(ctx.stmt())
        else:
            raise errors.AtoError("Unexpected block type")

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> OptionallyNamedItem:
        block_returns = self.visitBlock(ctx.block())

        if ctx.FROM():
            if not ctx.name_or_attr():
                raise errors.AtoError("Expected a name or attribute after 'from'")
            block_supers = (self.visit_ref_helper(ctx.name_or_attr()),)
        else:
            block_supers = self.visitBlocktype(ctx.blocktype())

        return (
            self.visit_ref_helper(ctx.name()),
            Object(
                src_ctx=ctx,
                supers=block_supers,
                locals_=block_returns,
            ),
        )

    def visitPindef_stmt(
        self, ctx: ap.Pindef_stmtContext
    ) -> OptionallyNamedItems:
        ref = self.visit_ref_helper(ctx.totally_an_integer() or ctx.name())

        if not ref:
            raise errors.AtoError("Pins must have a name")

        # TODO: reimplement this error handling at the above level
        created_pin = Object(
            src_ctx=ctx,
            supers=PIN,
        )

        return OptionallyNamedItems((ref, created_pin),)

    def visitSignaldef_stmt(
        self, ctx: ap.Signaldef_stmtContext
    ) -> OptionallyNamedItems:
        name = self.visit_ref_helper(ctx.name())

        # TODO: provide context of where this error was found within the file
        if not name:
            raise errors.AtoError("Signals must have a name")

        created_signal = Object(
            src_ctx=ctx,
            supers=SIGNAL,
        )
        # TODO: reimplement this error handling at the above level
        # if name in self.scope:
        #     raise errors.AtoNameConflictError(
        #         f"Cannot redefine '{name}' in the same scope"
        #     )
        return OptionallyNamedItems((name, created_signal),)

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
                    src_ctx=ctx,
                    what=imported_element,
                    from_=from_file,
                ),
            ),
        )

    # if a signal or a pin def statement are executed during a connection, it is returned as well
    def visitConnectable(
        self, ctx: ap.ConnectableContext
    ) -> tuple[Ref, Optional[OptionallyNamedItem]]:
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
    ) -> OptionallyNamedItem:
        """
        Connect interfaces together
        """
        source_name, source = self.visitConnectable(ctx.connectable(0))
        target_name, target = self.visitConnectable(ctx.connectable(1))

        returns = [
            (
                None,
                Link(source_name, target_name, src_ctx=ctx),
            )
        ]

        # If the connect statement is also used to instantiate an element, add it to the return tuple
        if source:
            returns.append(source)

        if target:
            returns.append(target)

        return tuple(returns)

    def visitNew_stmt(self, ctx: ap.New_stmtContext) -> Object:
        new_object_name = self.visit_ref_helper(ctx.name_or_attr())

        return Object(
            supers=new_object_name,
            locals_=(),
            src_ctx=ctx,
        )

    def visitString(self, ctx: ap.StringContext) -> str:
        return ctx.getText().strip("\"'")

    def visitBoolean_(self, ctx: ap.Boolean_Context) -> bool:
        return ctx.getText().lower() == "true"

    def visitAssignable(
        self, ctx: ap.AssignableContext
    ) -> OptionallyNamedItem | int | float | str:
        """Yield something we can place in a set of locals."""
        if ctx.name_or_attr():
            raise errors.AtoError("Cannot directly reference another object like this. Use 'new' instead.")

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
                    src_ctx=ctx,
                    original=original_name,
                    replacement=replaced_name,
                ),
            ),
        )

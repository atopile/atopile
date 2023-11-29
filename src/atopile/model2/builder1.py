"""
This datamodel represents the code in a clean, simple and traversable way,
but doesn't resolve names of things.
In building this datamodel, we check for name collisions, but we don't resolve them yet.
"""
import enum
import itertools
import logging
from pathlib import Path
from typing import Iterable, Mapping, Optional

from antlr4 import ParserRuleContext

from .parse_utils import get_src_info_from_ctx
from atopile.address import AddrStr
from atopile.model2 import errors
from atopile.parser.AtopileParser import AtopileParser as ap
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor

from .datamodel import (
    COMPONENT_REF,
    INTERFACE_REF,
    MODULE_REF,
    PIN_REF,
    SIGNAL_REF,
    Import,
    Link,
    Object,
    Replace,
)
from .datatypes import KeyOptItem, KeyOptMap, Ref

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


MODULE = (MODULE_REF,)
COMPONENT = (COMPONENT_REF,)
PIN = (PIN_REF,)
SIGNAL = (SIGNAL_REF,)
INTERFACE = (INTERFACE_REF,)


def _attach_downward_info(obj: Object) -> None:
    """Fix the closure of an object."""
    if obj.closure is None:
        obj.closure = ()

    if obj.address is None:
        assert isinstance(obj.src_ctx, ParserRuleContext)
        obj.address = AddrStr.from_parts(path=get_src_info_from_ctx(obj.src_ctx)[0])

    local_closure = obj.closure + (obj,)

    for ref, local in obj.locals_:
        if isinstance(local, Object):
            assert len(ref) == 1
            local.closure = local_closure
            local.address = obj.address.add_node(ref[0])
            _attach_downward_info(local)


def build(paths_to_trees: Mapping[Path, ParserRuleContext], error_handler: errors.ErrorHandler) -> Mapping[Path, Object]:
    """Build the datamodel from an ANTLR context."""
    dizzy = Dizzy(error_handler)

    results: Mapping[Path, Object] = {}

    for path, tree in paths_to_trees.items():
        try:
            result = dizzy.visit(tree)
            assert isinstance(result, Object)
            _attach_downward_info(result)
            results[path] = result
        except errors.AtoError as e:
            error_handler.handle(e)

    return results


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
        error_handler: errors.ErrorHandler,
    ) -> None:
        self.error_handler = error_handler
        super().__init__()

    def defaultResult(self):
        return NOTHING

    def visit_iterable_helper(self, children: Iterable) -> KeyOptMap:
        """
        Visit multiple children and return a tuple of their results,
        discard any results that are NOTHING and flattening the children's results.
        It is assumed the children are returning their own OptionallyNamedItems.
        """
        results = (self.visit(child) for child in children)
        return KeyOptMap(itertools.chain(*filter(lambda x: x is not NOTHING, results)))

    def visitSimple_stmt(self, ctx: ap.Simple_stmtContext) -> _Sentinel | KeyOptItem:
        """
        This is practically here as a development shim to assert the result is as intended
        """
        result = self.visitChildren(ctx)
        if result is not NOTHING:
            assert isinstance(result, KeyOptMap)
            if len(result) > 0:
                assert isinstance(result[0], KeyOptItem)
                if result[0].ref is not None:
                    assert isinstance(result[0].ref, Ref)
                assert len(result[0]) == 2
        return result

    def visitStmt(self, ctx: ap.StmtContext) -> KeyOptMap:
        """
        Ensure consistency of return type
        """
        if ctx.simple_stmts():
            value = self.visitSimple_stmts(ctx.simple_stmts())
        elif ctx.compound_stmt():
            value = KeyOptMap((self.visit(ctx.compound_stmt()),))
        else:
            self.error_handler.handle(errors.AtoError("Unexpected statement type"))
            value = NOTHING
        return value

    def visitSimple_stmts(self, ctx: ap.Simple_stmtsContext) -> KeyOptMap:
        return self.visit_iterable_helper(ctx.simple_stmt())

    def visitTotally_an_integer(self, ctx: ap.Totally_an_integerContext) -> int:
        text = ctx.getText()
        try:
            return int(text)
        except ValueError:
            self.error_handler.handle(
                errors.AtoTypeError(f"Expected an integer, but got {text}")
            )
            return NOTHING

    def visitFile_input(self, ctx: ap.File_inputContext) -> Object:
        locals_ = self.visit_iterable_helper(ctx.stmt())

        return Object(
            locals_=locals_,
            supers_refs=MODULE,
            src_ctx=ctx,
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
                self.error_handler.handle(
                    errors.AtoError(f"Unknown block type '{block_type_name}'")
                )
                return NOTHING

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
            return Ref.from_one(str(self.visit(ctx)))
        if isinstance(ctx, (ap.AttrContext, ap.Name_or_attrContext)):
            return Ref(
                map(str, self.visit(ctx)),
            )
        self.error_handler.handle(errors.AtoError(f"Unknown reference type: {type(ctx)}"))
        return NOTHING

    def visitName(self, ctx: ap.NameContext) -> str | int:
        """
        If this is an int, convert it to one (for pins), else return the name as a string.
        """
        try:
            return int(ctx.getText())
        except ValueError:
            return ctx.getText()

    def visitAttr(self, ctx: ap.AttrContext) -> Ref:
        return Ref(self.visitName(name) for name in ctx.name())  # Comprehension

    def visitName_or_attr(self, ctx: ap.Name_or_attrContext) -> Ref:
        if ctx.name():
            name = self.visitName(ctx.name())
            return Ref.from_one(name)
        elif ctx.attr():
            return self.visitAttr(ctx.attr())

        self.error_handler.handle(errors.AtoError("Expected a name or attribute"))
        return NOTHING

    def visitBlock(self, ctx) -> KeyOptMap:
        if ctx.simple_stmts():
            return self.visitSimple_stmts(ctx.simple_stmts())
        elif ctx.stmt():
            return self.visit_iterable_helper(ctx.stmt())
        else:
            self.error_handler.handle(errors.AtoError("Unexpected block type"))
            return NOTHING

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> KeyOptItem:
        block_returns = self.visitBlock(ctx.block())

        if ctx.FROM():
            if not ctx.name_or_attr():
                self.error_handler.handle(
                    errors.AtoError("Expected a name or attribute after 'from'")
                )
                return NOTHING
            block_supers = (self.visit_ref_helper(ctx.name_or_attr()),)
        else:
            block_supers = self.visitBlocktype(ctx.blocktype())

        return KeyOptItem.from_kv(
            self.visit_ref_helper(ctx.name()),
            Object(
                supers_refs=block_supers,
                locals_=block_returns,
                src_ctx=ctx,
            ),
        )

    def visitPindef_stmt(self, ctx: ap.Pindef_stmtContext) -> KeyOptMap:
        ref = self.visit_ref_helper(ctx.totally_an_integer() or ctx.name())

        if not ref:
            self.error_handler.handle(errors.AtoError("Pins must have a name"))
            return NOTHING

        # TODO: reimplement this error handling at the above level
        created_pin = Object(
            supers_refs=PIN,
            locals_=KeyOptMap(),
            src_ctx=ctx,
        )

        return KeyOptMap.from_kv(ref, created_pin)

    def visitSignaldef_stmt(self, ctx: ap.Signaldef_stmtContext) -> KeyOptMap:
        name = self.visit_ref_helper(ctx.name())

        # TODO: provide context of where this error was found within the file
        if not name:
            self.error_handler.handle(errors.AtoError("Signals must have a name"))
            return NOTHING

        created_signal = Object(
            supers_refs=SIGNAL,
            locals_=KeyOptMap(),
            src_ctx=ctx,
        )
        # TODO: reimplement this error handling at the above level
        # if name in self.scope:
        #    .handle_error.handel_error(errors.AtoNameConflictError()
        #         f"Cannot redefine '{name}' in the same scope"
        #     )
        return KeyOptMap.from_kv(name, created_signal)

    # Import statements have no ref
    def visitImport_stmt(self, ctx: ap.Import_stmtContext) -> KeyOptMap:
        from_file: str = self.visitString(ctx.string())
        imported_element = self.visit_ref_helper(ctx.name_or_attr())

        if not from_file:
            self.error_handler.handle(
                errors.AtoError("Expected a 'from <file-path>' after 'import'")
            )
            return NOTHING
        if not imported_element:
            self.error_handler.handle(
                errors.AtoError("Expected a name or attribute to import after 'import'")
            )
            return NOTHING

        if imported_element == "*":
            # import everything
            raise NotImplementedError("import *")

        import_ = Import(
            what_ref=imported_element,
            from_name=from_file,
            src_ctx=ctx,
        )

        return KeyOptMap.from_kv(imported_element, import_)

    # if a signal or a pin def statement are executed during a connection, it is returned as well
    def visitConnectable(
        self, ctx: ap.ConnectableContext
    ) -> tuple[Ref, Optional[KeyOptItem]]:
        if ctx.name_or_attr():
            # Returns a tuple
            return self.visit_ref_helper(ctx.name_or_attr()), None
        elif ctx.numerical_pin_ref():
            return self.visit_ref_helper(ctx.numerical_pin_ref()), None
        elif ctx.pindef_stmt() or ctx.signaldef_stmt():
            connectable: KeyOptMap = self.visitChildren(ctx)
            # return the object's ref and the created object itself
            ref = connectable[0][0]
            assert ref is not None
            return ref, connectable[0]
        else:
            raise ValueError("Unexpected context in visitConnectable")

    def visitConnect_stmt(self, ctx: ap.Connect_stmtContext) -> KeyOptMap:
        """
        Connect interfaces together
        """
        source_name, source = self.visitConnectable(ctx.connectable(0))
        target_name, target = self.visitConnectable(ctx.connectable(1))

        returns = [
            KeyOptItem.from_kv(
                None,
                Link(source_name, target_name, src_ctx=ctx),
            )
        ]

        # If the connect statement is also used to instantiate
        # an element, add it to the return tuple
        if source:
            returns.append(source)

        if target:
            returns.append(target)

        return KeyOptMap(returns)

    def visitNew_stmt(self, ctx: ap.New_stmtContext) -> Object:
        class_to_init = self.visit_ref_helper(ctx.name_or_attr())

        return Object(
            supers_refs=(class_to_init,),
            locals_=KeyOptMap(),
            src_ctx=ctx,
        )

    def visitString(self, ctx: ap.StringContext) -> str:
        return ctx.getText().strip("\"'")

    def visitBoolean_(self, ctx: ap.Boolean_Context) -> bool:
        return ctx.getText().lower() == "true"

    def visitAssignable(
        self, ctx: ap.AssignableContext
    ) -> KeyOptItem | int | float | str:
        """Yield something we can place in a set of locals."""
        if ctx.name_or_attr():
            raise errors.AtoError(
                "Cannot directly reference another object like this. Use 'new' instead."
            )

        if ctx.new_stmt():
            return self.visit(ctx.new_stmt())

        if ctx.NUMBER():
            value = float(ctx.NUMBER().getText())
            return int(value) if value.is_integer() else value

        if ctx.string():
            return self.visitString(ctx)

        if ctx.boolean_():
            return self.visitBoolean_(ctx.boolean_())

        raise errors.AtoError("Unexpected assignable type")

    def visitAssign_stmt(self, ctx: ap.Assign_stmtContext) -> KeyOptMap:
        assigned_value_name = self.visitName_or_attr(ctx.name_or_attr())
        assigned_value = self.visitAssignable(ctx.assignable())

        return KeyOptMap.from_kv(assigned_value_name, assigned_value)

    def visitRetype_stmt(self, ctx: ap.Retype_stmtContext) -> KeyOptMap:
        """
        This statement type will replace an existing block with a new one of a subclassed type

        Since there's no way to delete elements, we can be sure that the subclass is
        a superset of the superclass (confusing linguistically, makes sense logically)
        """
        original_name = self.visit_ref_helper(ctx.name_or_attr(0))
        replaced_name = self.visit_ref_helper(ctx.name_or_attr(1))

        replace = Replace(
            src_ctx=ctx,
            original_ref=original_name,
            replacement_ref=replaced_name,
        )

        return KeyOptMap.from_kv(None, replace)

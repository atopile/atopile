"""
This datamodel represents the code in a clean, simple and traversable way,
but doesn't resolve names of things.
In building this datamodel, we check for name collisions, but we don't resolve them yet.
"""
import enum
import logging
from typing import Iterable, Optional

import toolz
from antlr4 import ParserRuleContext

from atopile.address import AddrStr
from atopile.model2 import errors
from atopile.model2.datatypes import KeyOptItem, KeyOptMap, Ref
from atopile.model2.parse_utils import get_src_info_from_ctx
from atopile.parser.AtopileParser import AtopileParser as ap
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor

from .datamodel import (
    COMPONENT_REF,
    INTERFACE_REF,
    MODULE_REF,
    PIN_REF,
    SIGNAL_REF,
    Import,
    LinkDef,
    Object,
    Replace,
)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class _Sentinel(enum.Enum):
    NOTHING = enum.auto()


NOTHING = _Sentinel.NOTHING


def _attach_downward_info(obj: Object) -> None:
    """Fix the closure of an object."""
    local_closure = (obj,) + obj.closure
    for ref, local in obj.objs.items():
        if isinstance(local, Object):
            assert len(ref) == 1
            local.closure = local_closure
            local.ref = obj.ref.add_name(ref[0])
            local.address = obj.address.add_node(ref[0])
            _attach_downward_info(local)


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

    def build(self, ctx: ParserRuleContext) -> Object:
        """
        Build the object from the given context
        """
        obj = self.visit(ctx)
        assert isinstance(obj, Object)
        assert isinstance(obj.src_ctx, ParserRuleContext)

        obj.closure = ()
        obj.ref = Ref.empty()
        obj.address = AddrStr.from_parts(
            path = get_src_info_from_ctx(obj.src_ctx)[0]
        )

        _attach_downward_info(obj)

        return obj

    def defaultResult(self):
        """
        Override the default "None" return type
        (for things that return nothing) with the Sentinel NOTHING
        """
        return NOTHING

    def visit_iterable_helper(
        self,
        children: Iterable
    ) -> tuple[list[errors.AtoError], KeyOptMap]:
        """
        Visit multiple children and return a tuple of their results,
        discard any results that are NOTHING and flattening the children's results.
        It is assumed the children are returning their own OptionallyNamedItems.
        """

        _errors = []

        def __visit(child: ParserRuleContext) -> Iterable[_Sentinel | KeyOptItem]:
            try:
                child_result = self.visit(child)
                assert isinstance(child_result, KeyOptMap)
                return child_result
            except errors.AtoError as err:
                _errors.append(err)
                self.error_handler.handle(err)
                return (NOTHING,)

        items: Iterable[KeyOptItem] = toolz.pipe(
            children,                                          # stick in data
            toolz.curried.map(__visit),                        # visit each child
            toolz.curried.concat,                              # flatten the results
            toolz.curried.filter(lambda x: x is not NOTHING),  # filter out nothings
            toolz.curried.map(KeyOptItem)                      # ensure they are all KeyOptItem
        )

        return _errors, KeyOptMap(items)

    def make_object(
        self,
        locals_: KeyOptMap,
        super_ref: Ref,
        src_ctx: ParserRuleContext,
        errors_: Optional[list[errors.AtoError]] = None,
    ) -> Object:
        """Make an Object."""
        obj = Object(
            super_ref=super_ref,
            src_ctx=src_ctx,
            errors=errors_ or [],
        )

        # find name conflicts
        def __get_effective_name(item: KeyOptItem) -> str:
            key, value = item
            if isinstance(value, Import):
                # Looking up imports is a little weird
                # they will cause conflicts if they share a name with another import
                return key[:1]

            # default case
            return key

        name_usage = toolz.groupby(__get_effective_name, locals_)
        for name, usages in name_usage.items():
            if len(usages) > 1:
                # TODO: make this error more friendly by listing the things that share this name
                raise errors.AtoNameConflictError.from_ctx(
                    f"Conflicting name '{name}'",
                    obj.src_ctx
                )

        # stick all the locals in the right buckets
        for ref, local in locals_:
            try:
                if isinstance(local, Object):
                    if len(ref) > 1:
                        raise errors.AtoError(f"Cannot implicitly nest objects: {ref}")
                    obj.objs[ref[0]] = local
                elif isinstance(local, Import):
                    obj.imports[ref] = local
                elif isinstance(local, Replace):
                    obj.replacements.append(local)
                elif isinstance(local, LinkDef):
                    if ref:
                        raise NotImplementedError("Named links not yet supported")
                    obj.links.append(local)
                elif isinstance(local, (int, float, str, bool)):
                    # TODO: make a parameter object
                    if len(ref) == 1:
                        obj.data[ref[0]] = local
                    else:
                        obj.instance_overrides[ref] = local

                else:
                    raise errors.AtoTypeError.from_ctx(
                        f"Unknown local type: {type(local)} of {ref}",
                        obj.src_ctx
                    )

            except errors.AtoError as err:
                self.error_handler.handle(err)
                obj.errors.append(err)

        return obj

    def visitSimple_stmt(self, ctx: ap.Simple_stmtContext) -> _Sentinel | KeyOptItem:
        """
        This is practically here as a development shim to assert the result is as intended
        """
        result = self.visitChildren(ctx)
        if result is not NOTHING:
            if len(result) > 0:
                assert len(result[0]) == 2
        return result

    def visitStmt(self, ctx: ap.StmtContext) -> KeyOptMap:
        """
        Ensure consistency of return type.
        We choose to raise any below exceptions here, because stmts can be nested,
        and raising exceptions serves as our collection mechanism.
        """
        if ctx.simple_stmts():
            stmt_errors, stmt_returns = self.visitSimple_stmts(ctx.simple_stmts())

            if stmt_errors:
                if len(stmt_errors) == 1:
                    raise stmt_errors[0]
                else:
                    raise errors.AtoErrorGroup.from_ctx(
                        "Errors occured in nested statements",
                        stmt_errors,
                        ctx
                    )

            return stmt_returns
        elif ctx.compound_stmt():
            item = self.visit(ctx.compound_stmt())
            assert isinstance(item, KeyOptItem)
            return KeyOptMap.from_item(item)

        raise TypeError("Unexpected statement type")

    def visitSimple_stmts(self, ctx: ap.Simple_stmtsContext) -> tuple[list[errors.AtoError], KeyOptMap]:
        return self.visit_iterable_helper(ctx.simple_stmt())

    def visitTotally_an_integer(self, ctx: ap.Totally_an_integerContext) -> int:
        text = ctx.getText()
        try:
            return int(text)
        except ValueError:
            raise errors.AtoTypeError.from_ctx(f"Expected an integer, but got {text}", ctx)  # pylint: disable=raise-missing-from

    def visitFile_input(self, ctx: ap.File_inputContext) -> Object:
        file_errors, locals_ = self.visit_iterable_helper(ctx.stmt())

        return self.make_object(
            locals_=locals_,
            super_ref=MODULE_REF,
            src_ctx=ctx,
            errors_=file_errors,
        )

    def visitBlocktype(self, ctx: ap.BlocktypeContext) -> Ref:
        block_type_name = ctx.getText()
        match block_type_name:
            case "module":
                return MODULE_REF
            case "component":
                return COMPONENT_REF
            case "interface":
                return INTERFACE_REF
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
            (
                ap.NameContext,
                ap.Totally_an_integerContext,
                ap.Numerical_pin_refContext
            ),
        ):
            return Ref.from_one(str(self.visit(ctx)))
        if isinstance(ctx, (ap.AttrContext, ap.Name_or_attrContext)):
            return Ref(
                map(str, self.visit(ctx)),
            )
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
        return Ref(self.visitName(name) for name in ctx.name())  # Comprehension

    def visitName_or_attr(self, ctx: ap.Name_or_attrContext) -> Ref:
        if ctx.name():
            name = self.visitName(ctx.name())
            return Ref.from_one(name)
        elif ctx.attr():
            return self.visitAttr(ctx.attr())

        raise errors.AtoError("Expected a name or attribute")

    def visitBlock(self, ctx) -> tuple[list[errors.AtoError], KeyOptMap]:
        if ctx.simple_stmts():
            return self.visitSimple_stmts(ctx.simple_stmts())
        elif ctx.stmt():
            return self.visit_iterable_helper(ctx.stmt())
        raise ValueError  # this should be protected because it shouldn't be parseable

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> KeyOptItem:
        block_errors, block_returns = self.visitBlock(ctx.block())

        if ctx.FROM():
            if not ctx.name_or_attr():
                raise errors.AtoSyntaxError("Expected a name or attribute after 'from'")
            block_super = (self.visit_ref_helper(ctx.name_or_attr()),)
        else:
            block_super = self.visitBlocktype(ctx.blocktype())

        return KeyOptItem.from_kv(
            self.visit_ref_helper(ctx.name()),
            self.make_object(
                super_ref=block_super,
                locals_=block_returns,
                src_ctx=ctx,
                errors_=block_errors,
            ),
        )

    def visitPindef_stmt(self, ctx: ap.Pindef_stmtContext) -> KeyOptMap:
        ref = self.visit_ref_helper(ctx.totally_an_integer() or ctx.name())
        if not ref:
            raise errors.AtoError("Pins must have a name")

        created_pin = self.make_object(
            super_ref=PIN_REF,
            locals_=KeyOptMap(),
            src_ctx=ctx,
        )

        return KeyOptMap.from_kv(ref, created_pin)

    def visitSignaldef_stmt(self, ctx: ap.Signaldef_stmtContext) -> KeyOptMap:
        name = self.visit_ref_helper(ctx.name())
        if not name:
            raise errors.AtoError("Signals must have a name")

        created_signal = self.make_object(
            super_ref=SIGNAL_REF,
            locals_=KeyOptMap(),
            src_ctx=ctx,
        )
        return KeyOptMap.from_kv(name, created_signal)

    # Import statements have no ref
    def visitImport_stmt(self, ctx: ap.Import_stmtContext) -> KeyOptMap:
        from_file: str = self.visitString(ctx.string())
        imported_element = self.visit_ref_helper(ctx.name_or_attr())

        _errors = []

        if not from_file:
            _errors.append(errors.AtoError("Expected a 'from <file-path>' after 'import'"))
        if not imported_element:
            _errors.append(errors.AtoError("Expected a name or attribute to import after 'import'"))

        if imported_element == "*":
            # import everything
            raise NotImplementedError("import *")

        for error in _errors:
            self.error_handler.handle(error)

        import_ = Import(
            what_ref=imported_element,
            from_name=from_file,
            src_ctx=ctx,
            errors=_errors
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
                LinkDef(source_name, target_name, src_ctx=ctx),
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

        return self.make_object(
            super_ref=class_to_init,
            locals_=KeyOptMap(),
            src_ctx=ctx,
        )

    def visitString(self, ctx: ap.StringContext) -> str:
        return ctx.getText().strip("\"'")

    def visitBoolean_(self, ctx: ap.Boolean_Context) -> bool:
        return ctx.getText().lower() == "true"

    def visitAssignable(
        self, ctx: ap.AssignableContext
    ) -> Object | int | float | str | bool:
        """Yield something we can place in a set of locals."""
        if ctx.name_or_attr():
            raise errors.AtoError(
                "Cannot directly reference another object like this. Use 'new' instead."
            )

        if ctx.new_stmt():
            return self.visitNew_stmt(ctx.new_stmt())

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

"""
Build faebryk core objects from ato DSL.
"""

import itertools
import logging
import operator
import os
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import (
    Any,
    Iterable,
    Sequence,
    Type,
    cast,
)

from antlr4 import ParserRuleContext
from pint import UndefinedUnitError

import faebryk.library._F as F
import faebryk.libs.library.L as L
from atopile import address, config, errors
from atopile._shim import GlobalShims, has_ato_cmp_attrs, shim_map
from atopile.datatypes import KeyOptItem, KeyOptMap, Ref, StackList
from atopile.parse import parser
from atopile.parser.AtoParser import AtoParser as ap
from atopile.parser.AtoParserVisitor import AtoParserVisitor
from faebryk.core.node import NodeException
from faebryk.core.parameter import (
    Arithmetic,
    ConstrainableExpression,
    GreaterOrEqual,
    GreaterThan,
    IsSubset,
    LessOrEqual,
    LessThan,
    Max,
    Min,
    Parameter,
)
from faebryk.core.trait import Trait
from faebryk.libs.exceptions import (
    accumulate,
    downgrade,
    iter_through_errors,
    suppress_after_count,
)
from faebryk.libs.library.L import Range, Single
from faebryk.libs.sets.quantity_sets import Quantity_Interval, Quantity_Set
from faebryk.libs.sets.sets import BoolSet
from faebryk.libs.units import (
    HasUnit,
    P,
    Quantity,
    UnitCompatibilityError,
    dimensionless,
)
from faebryk.libs.units import (
    Unit as UnitType,
)
from faebryk.libs.util import (
    FuncDict,
    cast_assert,
    has_attr_or_property,
    has_instance_settable_attr,
    import_from_path,
)

logger = logging.getLogger(__name__)


Numeric = Parameter | Arithmetic | Quantity_Set


class from_dsl(Trait.decless()):
    def __init__(self, src_ctx: ParserRuleContext) -> None:
        super().__init__()
        self.src_ctx = src_ctx


class BasicsMixin:
    def visitName(self, ctx: ap.NameContext) -> str:
        """
        If this is an int, convert it to one (for pins),
        else return the name as a string.
        """
        return ctx.getText()

    def visitAttr(self, ctx: ap.AttrContext) -> Ref:
        return Ref([self.visitName(name) for name in ctx.name()])

    def visitName_or_attr(self, ctx: ap.Name_or_attrContext) -> Ref:
        if ctx.name():
            return Ref.from_one(self.visitName(ctx.name()))
        elif ctx.attr():
            return self.visitAttr(ctx.attr())

        raise errors.UserException.from_ctx(ctx, "Expected a name or attribute")

    def visitString(self, ctx: ap.StringContext) -> str:
        raw: str = ctx.getText()
        return raw.strip("\"'")

    def visitBoolean_(self, ctx: ap.Boolean_Context) -> bool:
        raw: str = ctx.getText()

        if raw.lower() == "true":
            return True
        elif raw.lower() == "false":
            return False

        raise errors.UserException.from_ctx(ctx, f"Expected a boolean value, got {raw}")


class NOTHING:
    """A sentinel object to represent a "nothing" return value."""


class SkipPriorFailedException(Exception):
    """Raised to skip a statement in case a dependency already failed"""


class DeprecatedException(errors.UserException):
    """
    Raised when a deprecated feature is used.
    """

    def get_frozen(self) -> tuple:
        # TODO: this is a bit of a hack to make the logger de-dup these for us
        return errors._BaseBaseUserException.get_frozen(self)


class SequenceMixin:
    """
    The base translator is responsible for methods common to
    navigating from the top of the AST including how to process
    errors, and commonising return types.
    """

    def defaultResult(self):
        """
        Override the default "None" return type
        (for things that return nothing) with the Sentinel NOTHING
        """
        return NOTHING

    def visit_iterable_helper(self, children: Iterable) -> KeyOptMap:
        """
        Visit multiple children and return a tuple of their results,
        discard any results that are NOTHING and flattening the children's results.
        It is assumed the children are returning their own OptionallyNamedItems.
        """

        def _visit():
            for err_cltr, child in iter_through_errors(
                children,
                errors._BaseBaseUserException,
                SkipPriorFailedException,
            ):
                with err_cltr():
                    # Since we're in a SequenceMixin, we need to cast self to the visitor type # noqa: E501  # pre-existing
                    child_result = cast(AtoParserVisitor, self).visit(child)
                    if child_result is not NOTHING:
                        yield child_result

        child_results = chain.from_iterable(_visit())
        child_results = filter(lambda x: x is not NOTHING, child_results)
        child_results = KeyOptMap(KeyOptItem(cr) for cr in child_results)

        return KeyOptMap(child_results)

    def visitFile_input(self, ctx: ap.File_inputContext) -> KeyOptMap:
        return self.visit_iterable_helper(ctx.stmt())

    def visitSimple_stmts(self, ctx: ap.Simple_stmtsContext) -> KeyOptMap:
        return self.visit_iterable_helper(ctx.simple_stmt())

    def visitBlock(self, ctx: ap.BlockContext) -> KeyOptMap:
        if ctx.stmt():
            return self.visit_iterable_helper(ctx.stmt())
        if ctx.simple_stmts():
            return self.visitSimple_stmts(ctx.simple_stmts())

        raise ValueError  # this should be protected because it shouldn't be parseable


class BlockNotFoundError(errors.UserKeyError):
    """
    Raised when a block doesn't exist.
    """


@dataclass
class Context:
    """~A metaclass to hold context/origin information on ato classes."""

    @dataclass
    class ImportPlaceholder:
        ref: Ref
        from_path: str
        original_ctx: ParserRuleContext

    # Location information re. the source of this module
    file_path: Path | None

    # Scope information
    scope_ctx: ap.BlockdefContext | ap.File_inputContext
    refs: dict[Ref, Type[L.Node] | ap.BlockdefContext | ImportPlaceholder]


class Wendy(BasicsMixin, SequenceMixin, AtoParserVisitor):  # type: ignore  # Overriding base class makes sense here
    """
    Wendy is Bob's business partner and fellow builder in the children's TV series
    "Bob the Builder." She is a skilled construction worker who often manages the
    business side of their building company while also participating in hands-on
    construction work. Wendy is portrayed as capable, practical and level-headed,
    often helping to keep projects organized and on track. She wears a green safety
    helmet and work clothes, and is known for her competence in operating various
    construction vehicles and equipment.

    Wendy also knows where to find the best building supplies.
    """

    def visitImport_stmt(
        self, ctx: ap.Import_stmtContext
    ) -> KeyOptMap[tuple[Context.ImportPlaceholder, ap.Import_stmtContext]]:
        if from_path := ctx.string():
            lazy_imports = [
                Context.ImportPlaceholder(
                    ref=self.visitName_or_attr(name_or_attr),
                    from_path=self.visitString(from_path),
                    original_ctx=ctx,
                )
                for name_or_attr in ctx.name_or_attr()
            ]
            return KeyOptMap(
                KeyOptItem.from_kv(li.ref, (li, ctx)) for li in lazy_imports
            )

        else:
            # Standard library imports are special, and don't require a from path
            imports = []
            for collector, name_or_attr in iter_through_errors(ctx.name_or_attr()):
                with collector():
                    ref = self.visitName_or_attr(name_or_attr)
                    if len(ref) > 1:
                        raise errors.UserKeyError.from_ctx(
                            ctx, "Standard library imports must be single-name"
                        )

                    name = ref[0]
                    if not hasattr(F, name) or not issubclass(
                        getattr(F, name), (L.Module, L.ModuleInterface)
                    ):
                        raise errors.UserKeyError.from_ctx(
                            ctx, f"Unknown standard library module: '{name}'"
                        )

                    imports.append(KeyOptItem.from_kv(ref, (getattr(F, name), ctx)))

            return KeyOptMap(imports)

    # TODO: @v0.4 remove this deprecated import form
    _suppressor_visitDep_import_stmt = suppress_after_count(
        3,
        DeprecatedException,
        logger=logger,
        suppression_warning="Suppressing further deprecation warnings",
    )

    def visitDep_import_stmt(
        self, ctx: ap.Dep_import_stmtContext
    ) -> KeyOptMap[tuple[Context.ImportPlaceholder, ap.Dep_import_stmtContext]]:
        lazy_import = Context.ImportPlaceholder(
            ref=self.visitName_or_attr(ctx.name_or_attr()),
            from_path=self.visitString(ctx.string()),
            original_ctx=ctx,
        )
        with downgrade(DeprecatedException), self._suppressor_visitDep_import_stmt:
            raise DeprecatedException.from_ctx(
                ctx,
                "`import <something> from <path>` is deprecated and"
                " will be removed in a future version. Use "
                f"`from {ctx.string().getText()} import {ctx.name_or_attr().getText()}`"
                " instead.",
            )
        return KeyOptMap.from_kv(lazy_import.ref, (lazy_import, ctx))

    def visitBlockdef(
        self, ctx: ap.BlockdefContext
    ) -> KeyOptMap[tuple[ap.BlockdefContext, ap.BlockdefContext]]:
        ref = Ref.from_one(self.visitName(ctx.name()))
        return KeyOptMap.from_kv(ref, (ctx, ctx))

    def visitSimple_stmt(
        self, ctx: ap.Simple_stmtContext | Any
    ) -> (
        KeyOptMap[
            tuple[Context.ImportPlaceholder | ap.BlockdefContext, ParserRuleContext]
        ]
        | type[NOTHING]
    ):
        if ctx.import_stmt() or ctx.dep_import_stmt():
            return super().visitChildren(ctx)
        return NOTHING

    # TODO: @v0.4: remove this shimming
    @staticmethod
    def _find_shim(file_path: Path | None, ref: Ref) -> tuple[Type[L.Node], str] | None:
        if file_path is None:
            return None

        import_addr = address.AddrStr.from_parts(file_path, str(Ref(ref)))

        for shim_addr in shim_map:
            if import_addr.endswith(shim_addr):
                return shim_map[shim_addr]

        return None

    @classmethod
    def survey(
        cls, file_path: Path | None, ctx: ap.BlockdefContext | ap.File_inputContext
    ) -> Context:
        surveyor = cls()
        context = Context(file_path=file_path, scope_ctx=ctx, refs={})
        for ref, (item, item_ctx) in surveyor.visit(ctx):
            assert isinstance(item_ctx, ParserRuleContext)
            if ref in context.refs:
                # Downgrade the error in case we're shadowing things
                # Not limiting the number of times we show this warning
                # because they're pretty important and Wendy is well cached
                with downgrade(errors.UserKeyError):
                    raise errors.UserKeyError.from_ctx(
                        item_ctx,
                        f"`{ref}` already declared. Shadowing original."
                        " In the future this may be an error",
                    )

            # TODO: @v0.4: remove this shimming
            if shim := cls._find_shim(context.file_path, ref):
                shim_cls, preferred = shim

                if hasattr(item_ctx, "name"):
                    dep_ctx = item_ctx.name()  # type: ignore
                elif hasattr(item_ctx, "name_or_attr"):
                    dep_ctx = item_ctx.name_or_attr()  # type: ignore
                else:
                    dep_ctx = item_ctx

                with downgrade(DeprecatedException):
                    raise DeprecatedException.from_ctx(
                        dep_ctx,
                        f"`{ref}` is deprecated and will be removed in a future"
                        f" version. Use `{preferred}` instead.",
                    )

                context.refs[ref] = shim_cls
            else:
                context.refs[ref] = item

        return context


def _is_int(name: str) -> bool:
    try:
        int(name)
    except ValueError:
        return False
    return True


@contextmanager
def ato_error_converter():
    try:
        yield
    except NodeException as ex:
        if from_dsl_ := ex.node.try_get_trait(from_dsl):
            raise errors.UserException.from_ctx(from_dsl_.src_ctx, str(ex)) from ex
        else:
            raise ex


@contextmanager
def _attach_ctx_to_ex(ctx: ParserRuleContext, traceback: Sequence[ParserRuleContext]):
    try:
        yield
    except errors.UserException as ex:
        if ex.origin is None:
            ex.origin = ctx
            # only attach traceback if we're also setting the origin
            if ex.traceback is None:
                ex.traceback = traceback
        raise ex


_declaration_domain_to_unit = {
    "resistance": P.ohm,
    "capacitance": P.farad,
    "inductance": P.henry,
    "voltage": P.volt,
    "current": P.ampere,
    "power": P.watt,
    "frequency": P.hertz,
}


class Bob(BasicsMixin, SequenceMixin, AtoParserVisitor):  # type: ignore  # Overriding base class makes sense here
    """
    Bob is a general contractor who runs his own construction company in the town
    of Fixham Harbour (in earlier episodes, he was based in Bobsville). Recognizable
    by his blue jeans, checked shirt, yellow hard hat, and tool belt, Bob is known
    for his positive catchphrase "Can we fix it? Yes, we can!" He's portrayed as a
    friendly, optimistic problem-solver who takes pride in helping his community
    through various building and repair projects. Bob works closely with his team
    of anthropomorphic construction vehicles and his business partner Wendy,
    tackling each construction challenge with enthusiasm and determination. His
    character embodies values of teamwork, perseverance, and taking pride in one's
    work.
    """

    def __init__(self) -> None:
        super().__init__()
        self._scopes = FuncDict[ParserRuleContext, Context]()
        self._python_classes = FuncDict[ap.BlockdefContext, Type[L.Module]]()
        self._node_stack = StackList[L.Node]()
        self._traceback_stack = StackList[ParserRuleContext]()
        # TODO: add tracebacks if we keep this
        self._promised_params = FuncDict[L.Node, list[ParserRuleContext]]()
        self._param_assignments = FuncDict[
            Parameter,
            tuple[
                Range | Single | None,
                ParserRuleContext | None,
                Sequence[ParserRuleContext] | None,
            ],
        ]()
        self.search_paths: list[os.PathLike] = []

        # Keeps track of the nodes whose construction failed,
        # so we don't report dud key errors when it was a higher failure
        # that caused the node not to exist
        self._failed_nodes = FuncDict[L.Node, set[str]]()

    def build_ast(
        self, ast: ap.File_inputContext, ref: Ref, file_path: Path | None = None
    ) -> L.Node:
        """Build a Module from an AST and reference."""
        file_path = self._sanitise_path(file_path) if file_path else None
        context = self._index_ast(ast, file_path)
        return self._build(context, ref)

    def build_file(self, path: Path, ref: Ref) -> L.Node:
        """Build a Module from a file and reference."""
        context = self._index_file(self._sanitise_path(path))
        return self._build(context, ref)

    @property
    def modules(self) -> dict[address.AddrStr, Type[L.Module]]:
        """Conceptually similar to `sys.modules`"""

        # FIXME: this feels like a shit way to get addresses of the imported modules
        def _get_addr(ctx: ParserRuleContext):
            ref = tuple()
            ctx_ = ctx
            while ctx_ not in self._scopes:
                if isinstance(ctx_, ap.BlockdefContext):
                    ref = (ctx_.name().getText(),) + ref
                ctx_ = ctx_.parentCtx
                if ctx_ is None:
                    return None

            return address.AddrStr.from_parts(
                self._scopes[ctx_].file_path, str(Ref(ref))
            )

        return {
            addr: cls
            for ctx, cls in self._python_classes.items()
            if (addr := _get_addr(ctx)) is not None
        }

    def _build(self, context: Context, ref: Ref) -> L.Node:
        if ref not in context.refs:
            raise errors.UserKeyError.from_ctx(
                context.scope_ctx, f"No declaration of `{ref}` in {context.file_path}"
            )
        try:
            class_ = self._get_referenced_class(context.scope_ctx, ref)
            if not isinstance(class_, ap.BlockdefContext):
                raise errors.UserNotImplementedError(
                    "Can't initialize a fabll directly like this"
                )
            with self._traceback_stack.enter(class_.name()):
                with self._init_node(class_) as node:
                    node.add(F.is_app_root())
                return node
        except* SkipPriorFailedException:
            raise errors.UserException("Build failed")
        finally:
            self._finish()

    # TODO: @v0.4 remove this deprecated import form
    _suppressor_finish = suppress_after_count(
        3,
        DeprecatedException,
        logger=logger,
        suppression_warning="Suppressing further deprecation warnings",
    )

    def _finish(self):
        with accumulate(
            errors._BaseBaseUserException, SkipPriorFailedException
        ) as ex_acc:
            for param, (value, ctx, traceback) in self._param_assignments.items():
                with ex_acc.collect(), ato_error_converter():
                    if value is None:
                        ex = errors.UserKeyError.from_ctx(
                            ctx,
                            f"Parameter `{param}` never assigned",
                            traceback=traceback,
                        )
                        if param in self._promised_params:
                            raise ex
                        else:
                            with (
                                downgrade(DeprecatedException),
                                self._suppressor_finish,
                            ):
                                raise DeprecatedException.from_ctx(
                                    ctx,
                                    f"Parameter `{param}` declared but never assigned."
                                    " In the future this will be an error.",
                                    traceback=traceback,
                                )
                            continue

                    if param in self._promised_params:
                        del self._promised_params[param]

                    # Set final value of parameter
                    assert isinstance(
                        ctx, ParserRuleContext
                    )  # Since value and ctx should be None together

                    try:
                        param.constrain_subset(value)
                    except UnitCompatibilityError as ex:
                        raise errors.UserTypeError.from_ctx(
                            ctx, str(ex), traceback=traceback
                        ) from ex

            for param, ctxs in self._promised_params.items():
                for ctx in ctxs:
                    with ex_acc.collect():
                        raise errors.UserKeyError.from_ctx(
                            ctx, f"Attribute `{param}` referenced, but never assigned"
                        )

    @property
    def _current_node(self) -> L.Node:
        return self._node_stack[-1]

    def get_traceback(self) -> Sequence[ParserRuleContext]:
        """Return the current traceback, with sequential duplicates removed"""
        # Use dict ordering guarantees and key uniqueness to remove duplicates
        return list(dict.fromkeys(self._traceback_stack).keys())

    @staticmethod
    def _sanitise_path(path: os.PathLike) -> Path:
        return Path(path).expanduser().resolve().absolute()

    def _index_ast(
        self, ast: ap.File_inputContext, file_path: Path | None = None
    ) -> Context:
        if ast in self._scopes:
            return self._scopes[ast]

        context = Wendy.survey(file_path, ast)
        self._scopes[ast] = context
        return context

    def _index_file(self, file_path: Path) -> Context:
        ast = parser.get_ast_from_file(file_path)
        return self._index_ast(ast, file_path)

    def _get_search_paths(self, context: Context) -> list[Path]:
        search_paths = [Path(p) for p in self.search_paths]

        if context.file_path is not None:
            search_paths.insert(0, context.file_path.parent)

        try:
            prj_context = config.get_project_context()
        except ValueError:
            # No project context, so we can't import anything
            pass
        else:
            search_paths += [
                prj_context.src_path,
                prj_context.module_path,
            ]

        return search_paths

    def _import_item(
        self, context: Context, item: Context.ImportPlaceholder
    ) -> Type[L.Node] | ap.BlockdefContext:
        # Build up search paths to check for the import in
        # Iterate though them, checking if any contains the thing we're looking for
        search_paths = self._get_search_paths(context)
        for search_path in search_paths:
            candidate_from_path = search_path / item.from_path
            if candidate_from_path.exists():
                break
        else:
            raise errors.UserFileNotFoundError.from_ctx(
                item.original_ctx,
                f"Can't find {item.from_path} in {", ".join(map(str, search_paths))}",
            )

        from_path = self._sanitise_path(candidate_from_path)
        if from_path.suffix == ".py":
            try:
                node = import_from_path(from_path)
            except FileNotFoundError as ex:
                raise errors.UserImportNotFoundError.from_ctx(
                    item.original_ctx, str(ex)
                ) from ex

            for ref in item.ref:
                try:
                    node = getattr(node, ref)
                except AttributeError as ex:
                    raise errors.UserKeyError.from_ctx(
                        item.original_ctx, f"No attribute `{ref}` found on {node}"
                    ) from ex

            assert isinstance(node, type) and issubclass(node, L.Node)
            return node

        elif from_path.suffix == ".ato":
            context = self._index_file(from_path)
            if item.ref not in context.refs:
                raise errors.UserKeyError.from_ctx(
                    item.original_ctx, f"No declaration of `{item.ref}` in {from_path}"
                )
            node = context.refs[item.ref]

            if isinstance(node, Context.ImportPlaceholder):
                raise errors.UserTypeError.from_ctx(
                    item.original_ctx,
                    "Importing a import is not supported",
                )

            assert (
                isinstance(node, type)
                and issubclass(node, L.Node)
                or isinstance(node, ap.BlockdefContext | ap.File_inputContext)
            )
            return node

        else:
            raise errors.UserImportNotFoundError.from_ctx(
                item.original_ctx, f"Can't import file type {from_path.suffix}"
            )

    def _get_referenced_class(
        self, ctx: ParserRuleContext, ref: Ref
    ) -> Type[L.Node] | ap.BlockdefContext:
        """
        Returns the class / object referenced by the given ref,
        based on Bob's current context. The contextual nature
        of this means that it's only useful during the build process.
        """
        # No change in position from the current context
        # return self, eg the current parser context
        if ref == tuple():
            if isinstance(ctx, ap.BlockdefContext):
                return ctx
            else:
                raise ValueError(f"Can't get class `{ref}` from {ctx}")

        # Ascend the tree until we find a scope that has the ref within it
        ctx_ = ctx
        while ctx_ not in self._scopes:
            if ctx_.parentCtx is None:
                raise ValueError(f"No scope found for `{ref}`")
            ctx_ = ctx_.parentCtx

        context = self._scopes[ctx_]

        # FIXME: there are more cases to check here,
        # eg. if we have part of a ref resolved
        if ref not in context.refs:
            raise errors.UserKeyError.from_ctx(
                ctx, f"No class or block definition found for `{ref}`"
            )

        item = context.refs[ref]
        # Ensure the item is resolved, if not already
        if isinstance(item, Context.ImportPlaceholder):
            # TODO: search path for these imports
            item = self._import_item(context, item)
            context.refs[ref] = item

        return item

    @staticmethod
    def get_node_attr(node: L.Node, name: str) -> L.Node:
        if _is_int(name):
            name = f"_{name}"

        if has_attr_or_property(node, name):
            # Build-time attributes are attached as real attributes
            return getattr(node, name)
        elif name in node.runtime:
            # Runtime attributes are attached as runtime attributes
            return node.runtime[name]
        else:
            # Wah wah wah - we don't know what this is
            raise AttributeError(name=name, obj=node)

    def _get_referenced_node(self, ref: Ref, ctx: ParserRuleContext) -> L.Node:
        node = self._current_node
        for i, name in enumerate(ref):
            # Shim integer names to make valid python identifiers
            if _is_int(name):
                name = f"_{name}"

            try:
                node = self.get_node_attr(node, name)
            except AttributeError as ex:
                if name in self._failed_nodes.get(node, set()):
                    raise SkipPriorFailedException() from ex
                # Wah wah wah - we don't know what this is
                if ref[:i]:
                    msg = f"`{Ref(ref[:i])}` has no attribute `{name}`"
                else:
                    msg = f"No attribute `{name}`"
                raise errors.UserKeyError.from_ctx(
                    ctx, msg, traceback=self.get_traceback()
                ) from ex

        return node

    def _try_get_referenced_node(
        self, ref: Ref, ctx: ParserRuleContext
    ) -> L.Node | None:
        try:
            return self._get_referenced_node(ref, ctx)
        except errors.UserKeyError:
            return None

    def _new_node(
        self,
        item: ap.BlockdefContext | Type[L.Node],
        promised_supers: list[ap.BlockdefContext],
    ) -> tuple[L.Node, list[ap.BlockdefContext]]:
        """
        Kind of analogous to __new__ in Python, except that it's a factory

        Descends down the class hierarchy until it finds a known base class.
        As it descends, it logs all superclasses it encounters, as `promised_supers`.
        These are accumulated lowest (base-class) to highest (what was initialised).

        Once a base class is found, it creates a new class for each superclass that
        isn't already known, attaching the __atopile_src_ctx__ attribute to the new
        class.
        """
        if isinstance(item, type) and issubclass(item, L.Node):
            super_class = item
            for super_ctx in promised_supers:
                if super_ctx in self._python_classes:
                    super_class = self._python_classes[super_ctx]
                    continue

                assert issubclass(super_class, L.Node)

                # Create a new type with a more descriptive name
                type_name = super_ctx.name().getText()
                type_qualname = f"{super_class.__module__}.{type_name}"

                super_class = type(
                    type_name,  # Class name
                    (super_class,),  # Base classes
                    {
                        "__module__": super_class.__module__,
                        "__qualname__": type_qualname,
                        "__atopile_src_ctx__": super_ctx,
                    },
                )

                self._python_classes[super_ctx] = super_class

            assert issubclass(super_class, L.Node)
            return super_class(), promised_supers

        if isinstance(item, ap.BlockdefContext):
            # Find the superclass of the new node, if there's one defined
            block_type = item.blocktype()
            if super_ctx := item.blockdef_super():
                super_ref = self.visitName_or_attr(super_ctx.name_or_attr())
                # Create a base node to build off
                base_class = self._get_referenced_class(item, super_ref)
            else:
                # Create a shell of base-node to build off
                assert isinstance(block_type, ap.BlocktypeContext)
                if block_type.INTERFACE():
                    base_class = L.ModuleInterface
                elif block_type.COMPONENT():
                    base_class = L.Module
                elif block_type.MODULE():
                    base_class = L.Module
                else:
                    raise ValueError(f"Unknown block type `{block_type.getText()}`")

            # Descend into building the superclass. We've got no information
            # on when the super-chain will be resolved, so we need to promise
            # that this current blockdef will be visited as part of the init
            result = self._new_node(
                base_class,
                promised_supers=[item] + promised_supers,
            )

            return result

        # This should never happen
        raise ValueError(f"Unknown item type `{item}`")

    @contextmanager
    def _init_node(
        self, node_type: ap.BlockdefContext | Type[L.Node]
    ) -> Generator[L.Node, None, None]:
        """Kind of analogous to __init__ in Python, except that it's a factory"""
        new_node, promised_supers = self._new_node(
            node_type,
            promised_supers=[],
        )

        # Shim on component and module classes defined in ato
        # Do not shim fabll modules, or interfaces
        if isinstance(node_type, ap.BlockdefContext):
            if node_type.blocktype().COMPONENT() or node_type.blocktype().MODULE():
                # Some shims add the trait themselves
                if not new_node.has_trait(has_ato_cmp_attrs):
                    new_node.add(has_ato_cmp_attrs())

        yield new_node

        with self._node_stack.enter(new_node):
            for super_ctx in promised_supers:
                # TODO: this would be better if we had the
                # "from xyz" super in the traceback too
                with self._traceback_stack.enter(super_ctx.name()):
                    self.visitBlock(super_ctx.block())

    def _get_or_promise_param(
        self, node: L.Node, name: str, src_ctx: ParserRuleContext
    ) -> Parameter:
        """
        Get a param from a node. If it doesn't exist, create it and promise to assign
        it later. Used in forward-declaration.
        """
        try:
            node = self.get_node_attr(node, name)
        except AttributeError as ex:
            if name in self._failed_nodes.get(node, set()):
                raise SkipPriorFailedException() from ex
            # Wah wah wah - we don't know what this is
            raise errors.UserNotImplementedError.from_ctx(
                src_ctx,
                f"Parameter `{name}` not found and"
                " forward-declared params are not yet implemented",
                traceback=self.get_traceback(),
            ) from ex

        assert isinstance(node, Parameter)
        return node

    def _ensure_param(
        self,
        node: L.Node,
        name: str,
        unit: UnitType,
        src_ctx: ParserRuleContext,
    ) -> Parameter:
        """
        Ensure a node has a param with a given name
        If it already exists, check the unit is compatible and return it
        """
        try:
            param = self.get_node_attr(node, name)
        except AttributeError:
            # Here we attach only minimal information, so we can override it later
            param = node.add(
                Parameter(units=unit, domain=L.Domains.Numbers.REAL()), name=name
            )
        else:
            if not isinstance(param, Parameter):
                raise errors.UserTypeError.from_ctx(
                    src_ctx,
                    f"Cannot assign a parameter to `{name}` on `{node}` because its"
                    f" type is `{param.__class__.__name__}`",
                    traceback=self.get_traceback(),
                )

        if not param.units.is_compatible_with(unit):
            raise errors.UserIncompatibleUnitError.from_ctx(
                src_ctx,
                f"Given units ({unit}) are incompatible"
                f" with existing units ({param.units}).",
                traceback=self.get_traceback(),
            )

        return param

    def _record_failed_node(self, node: L.Node, name: str):
        self._failed_nodes.setdefault(node, set()).add(name)

    # TODO: @v0.4 remove this deprecated import form
    _suppressor_visitAssign_stmt = suppress_after_count(
        5,
        errors.UserException,
        logger=logger,
        suppression_warning="Suppressing further warnings of this type",
    )

    def visitAssign_stmt(self, ctx: ap.Assign_stmtContext):
        """Assignment values and create new instance of things."""
        assigned_ref = self.visitName_or_attr(ctx.name_or_attr())

        assigned_name: str = assigned_ref[-1]
        assignable_ctx = ctx.assignable()
        assert isinstance(assignable_ctx, ap.AssignableContext)
        target = self._get_referenced_node(Ref(assigned_ref[:-1]), ctx)

        ########## Handle New Statements ##########
        if new_stmt_ctx := assignable_ctx.new_stmt():
            if len(assigned_ref) > 1:
                raise errors.UserSyntaxError.from_ctx(
                    ctx,
                    f"Can't declare fields in a nested object `{assigned_ref}`",
                    traceback=self.get_traceback(),
                )

            assert isinstance(new_stmt_ctx, ap.New_stmtContext)
            ref = self.visitName_or_attr(new_stmt_ctx.name_or_attr())

            try:
                with self._traceback_stack.enter(new_stmt_ctx):
                    with self._init_node(
                        self._get_referenced_class(ctx, ref)
                    ) as new_node:
                        self._current_node.add(new_node, name=assigned_name)
                        new_node.add(from_dsl(ctx))
            except Exception:
                # Not a narrower exception because it's often an ExceptionGroup
                self._record_failed_node(self._current_node, assigned_name)
                raise

            return NOTHING

        ########## Handle Regular Assignments ##########
        value = self.visit(assignable_ctx)
        if assignable_ctx.literal_physical() or assignable_ctx.arithmetic_expression():
            unit = HasUnit.get_units(value)
            if provided_unit := self._try_get_unit_from_type_info(ctx.type_info()):
                if not provided_unit.is_compatible_with(unit):
                    raise errors.UserIncompatibleUnitError.from_ctx(
                        ctx,
                        f"Implied units ({unit}) are incompatible"
                        f" with explicit units ({provided_unit}).",
                        traceback=self.get_traceback(),
                    )
            param = self._ensure_param(target, assigned_name, unit, ctx)
            self._param_assignments[param] = (value, ctx, self.get_traceback())

        elif assignable_ctx.string() or assignable_ctx.boolean_():
            # Check if it's a property or attribute that can be set
            if has_instance_settable_attr(target, assigned_name):
                setattr(target, assigned_name, value)
            elif (
                # If ModuleShims has a settable property, use it
                hasattr(GlobalShims, assigned_name)
                and isinstance(getattr(GlobalShims, assigned_name), property)
                and getattr(GlobalShims, assigned_name).fset
            ):
                prop = cast_assert(property, getattr(GlobalShims, assigned_name))
                assert prop.fset is not None
                with (
                    downgrade(DeprecatedException, errors.UserNotImplementedError),
                    self._suppressor_visitAssign_stmt,
                    _attach_ctx_to_ex(ctx, self.get_traceback()),
                ):
                    prop.fset(target, value)
            else:
                # Strictly, these are two classes of errors that could use independent
                # suppression, but we'll just suppress them both collectively for now
                with downgrade(errors.UserException), self._suppressor_visitAssign_stmt:
                    raise errors.UserException.from_ctx(
                        ctx,
                        f"Ignoring assignment of `{value}` to `{assigned_name}` "
                        f"on `{target}`",
                        traceback=self.get_traceback(),
                    )

        else:
            raise ValueError(f"Unhandled assignable type `{assignable_ctx.getText()}`")

        return NOTHING

    # TODO: @v0.4 remove this deprecated import form
    _suppression_try_get_mif = suppress_after_count(
        3,
        DeprecatedException,
        logger=logger,
        suppression_warning="Suppressing further deprecation warnings",
    )

    def _try_get_mif(
        self, name: str, ctx: ParserRuleContext
    ) -> L.ModuleInterface | None:
        try:
            mif = self.get_node_attr(self._current_node, name)
        except AttributeError:
            return None

        if isinstance(mif, L.ModuleInterface):
            with downgrade(DeprecatedException), self._suppression_try_get_mif:
                raise DeprecatedException(
                    f"`{name}` already exists; skipping."
                    " In the future this will be an error."
                )
        else:
            raise errors.UserTypeError.from_ctx(
                ctx,
                f"`{name}` already exists.",
                traceback=self.get_traceback(),
            )

        return mif

    def visitPindef_stmt(
        self, ctx: ap.Pindef_stmtContext
    ) -> KeyOptMap[L.ModuleInterface]:
        if ctx.name():
            name = self.visitName(ctx.name())
        elif ctx.totally_an_integer():
            name = f"{ctx.totally_an_integer().getText()}"
        elif ctx.string():
            name = self.visitString(ctx.string())
        else:
            raise ValueError(f"Unhandled pin name type `{ctx}`")

        if mif := self._try_get_mif(name, ctx):
            return KeyOptMap.from_item(KeyOptItem.from_kv(Ref.from_one(name), mif))

        if shims_t := self._current_node.try_get_trait(has_ato_cmp_attrs):
            mif = shims_t.add_pin(name)
            return KeyOptMap.from_item(KeyOptItem.from_kv(Ref.from_one(name), mif))

        raise errors.UserTypeError.from_ctx(
            ctx,
            f"Can't declare pins on components of type {self._current_node}",
            traceback=self.get_traceback(),
        )

    def visitSignaldef_stmt(
        self, ctx: ap.Signaldef_stmtContext
    ) -> KeyOptMap[L.ModuleInterface]:
        name = self.visitName(ctx.name())
        # TODO: @v0.4: remove this protection
        if mif := self._try_get_mif(name, ctx):
            return KeyOptMap.from_item(KeyOptItem.from_kv(Ref.from_one(name), mif))

        mif = self._current_node.add(F.Electrical(), name=name)
        return KeyOptMap.from_item(KeyOptItem.from_kv(Ref.from_one(name), mif))

    # TODO: @v0.4 remove this deprecated import form
    _suppression_connect = suppress_after_count(
        3,
        DeprecatedException,
        logger=logger,
        suppression_warning="Suppressing further deprecation warnings",
    )

    def _connect(
        self, a: L.ModuleInterface, b: L.ModuleInterface, ctx: ParserRuleContext | None
    ):
        """
        FIXME: In ato, we allowed duck-typing of connectables
        We need to reconcile this with the strong typing
        in faebryk's connect method
        For now, we'll attempt to connect by name, and log a deprecation
        warning if that succeeds, else, re-raise the exception emitted
        by the connect method
        """
        try:
            # Try a proper connection
            a.connect(b)
        except NodeException as top_ex:
            # If that fails, try connecting via duck-typing
            for name, (c_a, c_b) in a.zip_children_by_name_with(
                b, L.ModuleInterface
            ).items():
                if c_a is None:
                    if has_attr_or_property(a, name):
                        c_a = getattr(a, name)
                    else:
                        raise

                if c_b is None:
                    if has_attr_or_property(b, name):
                        c_b = getattr(b, name)
                    else:
                        raise

                try:
                    self._connect(c_a, c_b, None)
                except NodeException:
                    raise top_ex

            else:
                # If we connect everything via name (and tried in the first place)
                # then we're good to go! We just need to tell everyone to probably not
                # do that in the future - and we're off!
                if ctx is not None:  # Check that this is the top-level _connect call
                    with downgrade(DeprecatedException), self._suppression_connect:
                        raise DeprecatedException.from_ctx(
                            ctx,
                            f"Connected `{a}` to `{b}` by duck-typing."
                            "They should be of the same type.",
                            traceback=self.get_traceback(),
                        )

    def visitConnect_stmt(self, ctx: ap.Connect_stmtContext):
        """Connect interfaces together"""
        connectables = [self.visitConnectable(c) for c in ctx.connectable()]
        for err_cltr, (a, b) in iter_through_errors(
            itertools.pairwise(connectables),
            errors._BaseBaseUserException,
            SkipPriorFailedException,
        ):
            with err_cltr():
                self._connect(a, b, ctx)

        return NOTHING

    def visitConnectable(self, ctx: ap.ConnectableContext) -> L.ModuleInterface:
        """Return the address of the connectable object."""
        if def_stmt := ctx.pindef_stmt() or ctx.signaldef_stmt():
            (_, mif), *_ = self.visit(def_stmt)
            return mif
        elif name_or_attr_ctx := ctx.name_or_attr():
            ref = self.visitName_or_attr(name_or_attr_ctx)
            node = self._get_referenced_node(ref, ctx)
            assert isinstance(node, L.ModuleInterface)
            return node
        elif numerical_ctx := ctx.numerical_pin_ref():
            pin_name = numerical_ctx.getText()
            ref = Ref(pin_name.split("."))
            node = self._get_referenced_node(ref, ctx)
            assert isinstance(node, L.ModuleInterface)
            return node
        else:
            raise ValueError(f"Unhandled connectable type `{ctx}`")

    def visitRetype_stmt(self, ctx: ap.Retype_stmtContext):
        from_ref, to_ref = map(self.visitName_or_attr, ctx.name_or_attr())
        from_node = self._get_referenced_node(from_ref, ctx)
        if not isinstance(from_node, L.Module):
            raise errors.UserTypeError.from_ctx(
                ctx,
                f"Can't specialize `{from_node}`",
                traceback=self.get_traceback(),
            )

        # TODO: consider extending this w/ the ability to specialize to an instance
        with self._traceback_stack.enter(ctx):
            with self._init_node(
                self._get_referenced_class(ctx, to_ref)
            ) as specialized_node:
                from_node.add(specialized_node)
        assert isinstance(specialized_node, L.Module)

        try:
            from_node.specialize(specialized_node)
        except* L.Module.InvalidSpecializationError as ex:
            raise errors.UserException.from_ctx(
                ctx,
                f"Can't specialize `{from_ref}` with `{to_ref}`:\n"
                + "\n".join(f" - {e.message}" for e in ex.exceptions),
                traceback=self.get_traceback(),
            ) from ex
        return NOTHING

    def visitBlockdef(self, ctx: ap.BlockdefContext):
        """Do nothing. Handled in Surveyor."""
        return NOTHING

    def visitImport_stmt(self, ctx: ap.Import_stmtContext):
        """Do nothing. Handled in Surveyor."""
        return NOTHING

    def visitDep_import_stmt(self, ctx: ap.Dep_import_stmtContext):
        """Do nothing. Handled in Surveyor."""
        return NOTHING

    def visitAssert_stmt(self, ctx: ap.Assert_stmtContext):
        comparisons = [c for _, c in self.visitComparison(ctx.comparison())]
        for cmp in comparisons:
            if isinstance(cmp, BoolSet):
                if not cmp:
                    raise errors.UserAssertionError.from_ctx(
                        ctx,
                        "Assertion failed",
                        traceback=self.get_traceback(),
                    )
            elif isinstance(cmp, ConstrainableExpression):
                cmp.constrain()
            else:
                raise ValueError(f"Unhandled comparison type {type(cmp)}")
        return NOTHING

    # Returns fab_param.ConstrainableExpression or BoolSet
    def visitComparison(
        self, ctx: ap.ComparisonContext
    ) -> KeyOptMap[ConstrainableExpression | BoolSet]:
        exprs = [
            self.visitArithmetic_expression(c)
            for c in [ctx.arithmetic_expression()]
            + [cop.getChild(0).arithmetic_expression() for cop in ctx.compare_op_pair()]
        ]
        op_strs = [
            cop.getChild(0).getChild(0).getText() for cop in ctx.compare_op_pair()
        ]

        predicates = []
        for (lh, rh), op_str in zip(itertools.pairwise(exprs), op_strs):
            match op_str:
                case "<":
                    op = LessThan
                case ">":
                    op = GreaterThan
                case "<=":
                    op = LessOrEqual
                case ">=":
                    op = GreaterOrEqual
                case "within":
                    op = IsSubset
                case _:
                    # We shouldn't be able to get here with parseable input
                    raise ValueError(f"Unhandled operator `{op_str}`")

            # TODO: should we be reducing here to a series of ANDs?
            predicates.append(op(lh, rh))

        return KeyOptMap([KeyOptItem.from_kv(None, p) for p in predicates])

    def visitArithmetic_expression(
        self, ctx: ap.Arithmetic_expressionContext
    ) -> Numeric:
        if ctx.OR_OP() or ctx.AND_OP():
            raise errors.UserTypeError.from_ctx(
                ctx,
                "Logical operations are not supported",
                traceback=self.get_traceback(),
            )
            lh = self.visitArithmetic_expression(ctx.arithmetic_expression())
            rh = self.visitSum(ctx.sum_())

            if ctx.OR_OP():
                return operator.or_(lh, rh)
            else:
                return operator.and_(lh, rh)

        return self.visitSum(ctx.sum_())

    def visitSum(self, ctx: ap.SumContext) -> Numeric:
        if ctx.ADD() or ctx.MINUS():
            lh = self.visitSum(ctx.sum_())
            rh = self.visitTerm(ctx.term())

            if ctx.ADD():
                return operator.add(lh, rh)
            else:
                return operator.sub(lh, rh)

        return self.visitTerm(ctx.term())

    def visitTerm(self, ctx: ap.TermContext) -> Numeric:
        if ctx.STAR() or ctx.DIV():
            lh = self.visitTerm(ctx.term())
            rh = self.visitPower(ctx.power())

            if ctx.STAR():
                return operator.mul(lh, rh)
            else:
                return operator.truediv(lh, rh)

        return self.visitPower(ctx.power())

    def visitPower(self, ctx: ap.PowerContext) -> Numeric:
        if ctx.POWER():
            base, exp = map(self.visitFunctional, ctx.functional())
            return operator.pow(base, exp)
        else:
            return self.visitFunctional(ctx.functional(0))

    def visitFunctional(self, ctx: ap.FunctionalContext) -> Numeric:
        if ctx.name():
            name = self.visitName(ctx.name())
            operands = [self.visitBound(b) for b in ctx.bound()]
            if name == "min":
                return Min(*operands)
            elif name == "max":
                return Max(*operands)
            else:
                raise errors.UserNotImplementedError.from_ctx(
                    ctx, f"Unknown function `{name}`"
                )
        else:
            return self.visitBound(ctx.bound(0))

    def visitBound(self, ctx: ap.BoundContext) -> Numeric:
        return self.visitAtom(ctx.atom())

    def visitAtom(self, ctx: ap.AtomContext) -> Numeric:
        if ctx.name_or_attr():
            ref = self.visitName_or_attr(ctx.name_or_attr())
            target = self._get_referenced_node(Ref(ref[:-1]), ctx)
            return self._get_or_promise_param(target, ref[-1], ctx)

        elif ctx.literal_physical():
            return self.visitLiteral_physical(ctx.literal_physical())

        elif group_ctx := ctx.arithmetic_group():
            assert isinstance(group_ctx, ap.Arithmetic_groupContext)
            return self.visitArithmetic_expression(group_ctx.arithmetic_expression())

        raise ValueError(f"Unhandled atom type `{ctx}`")

    def _get_unit_from_ctx(self, ctx: ParserRuleContext) -> UnitType:
        """Return a pint unit from a context."""
        unit_str = ctx.getText()
        try:
            return P.Unit(unit_str)
        except UndefinedUnitError as ex:
            raise errors.UserUnknownUnitError.from_ctx(
                ctx,
                f"Unknown unit `{unit_str}`",
                traceback=self.get_traceback(),
            ) from ex

    def visitLiteral_physical(
        self, ctx: ap.Literal_physicalContext
    ) -> Quantity_Interval:
        """Yield a physical value from a physical context."""
        if ctx.quantity():
            qty = self.visitQuantity(ctx.quantity())
            value = Single(qty)
        elif ctx.bilateral_quantity():
            value = self.visitBilateral_quantity(ctx.bilateral_quantity())
        elif ctx.bound_quantity():
            value = self.visitBound_quantity(ctx.bound_quantity())
        else:
            # this should be protected because it shouldn't be parseable
            raise ValueError
        return value

    def visitQuantity(self, ctx: ap.QuantityContext) -> Quantity:
        """Yield a physical value from an implicit quantity context."""
        raw: str = ctx.NUMBER().getText()
        if raw.startswith("0x"):
            value = int(raw, 16)
        else:
            value = float(raw)

        # Ignore the positive unary operator
        if ctx.MINUS():
            value = -value

        if unit_ctx := ctx.name():
            unit = self._get_unit_from_ctx(unit_ctx)
        else:
            unit = dimensionless

        return Quantity(value, unit)  # type: ignore

    def visitBilateral_quantity(
        self, ctx: ap.Bilateral_quantityContext
    ) -> Quantity_Interval:
        """Yield a physical value from a bilateral quantity context."""
        nominal_qty = self.visitQuantity(ctx.quantity())

        tol_ctx: ap.Bilateral_toleranceContext = ctx.bilateral_tolerance()
        tol_num = float(tol_ctx.NUMBER().getText())

        # Handle proportional tolerances
        if tol_ctx.PERCENT():
            tol_divider = 100
        elif tol_ctx.name() and tol_ctx.name().getText() == "ppm":
            tol_divider = 1e6
        else:
            tol_divider = None

        if tol_divider:
            if nominal_qty == 0:
                raise errors.UserException.from_ctx(
                    tol_ctx,
                    "Can't calculate tolerance percentage of a nominal value of zero",
                    traceback=self.get_traceback(),
                )

            # Calculate tolerance value from percentage/ppm
            tol_value = tol_num / tol_divider
            return Range.from_center_rel(nominal_qty, tol_value)

        # Ensure the tolerance has a unit
        if tol_name := tol_ctx.name():
            # In this case there's a named unit on the tolerance itself
            tol_qty = tol_num * self._get_unit_from_ctx(tol_name)
        elif nominal_qty.unitless:
            tol_qty = tol_num * dimensionless
        else:
            tol_qty = tol_num * nominal_qty.units

        # Ensure units on the nominal quantity
        if nominal_qty.unitless:
            nominal_qty = nominal_qty * HasUnit.get_units(tol_qty)

        # If the nominal has a unit, then we rely on the ranged value's unit compatibility # noqa: E501  # pre-existing
        if not nominal_qty.is_compatible_with(tol_qty):
            raise errors.UserTypeError.from_ctx(
                tol_name,
                f"Tolerance unit ({HasUnit.get_units(tol_qty)}) is not dimensionally"
                f" compatible with nominal unit ({nominal_qty.units})",
                traceback=self.get_traceback(),
            )

        return Range.from_center(nominal_qty, tol_qty)

    def visitBound_quantity(self, ctx: ap.Bound_quantityContext) -> Quantity_Interval:
        """Yield a physical value from a bound quantity context."""

        start, end = map(self.visitQuantity, ctx.quantity())

        # If only one of them has a unit, take the unit from the one which does
        if start.unitless and not end.unitless:
            start = start * end.units
        elif not start.unitless and end.unitless:
            end = end * start.units

        elif not start.is_compatible_with(end):
            # If they've both got units, let the RangedValue handle
            # the dimensional compatibility
            raise errors.UserTypeError.from_ctx(
                ctx,
                f"Tolerance unit ({end.units}) is not dimensionally"
                f" compatible with nominal unit ({start.units})",
                traceback=self.get_traceback(),
            )

        return Range(start, end)

    # TODO: @v0.4 remove this deprecated import form
    _suppressor_visitCum_assign_stmt = suppress_after_count(
        3,
        DeprecatedException,
        logger=logger,
        suppression_warning="Suppressing further deprecation warnings",
    )

    def visitCum_assign_stmt(self, ctx: ap.Cum_assign_stmtContext | Any):
        """
        Cumulative assignments can only be made on top of
        nothing (implicitly declared) or declared, but undefined values.

        Unlike assignments, they may not implicitly declare an attribute.
        """
        assignee_ref = self.visitName_or_attr(ctx.name_or_attr())
        target = self._get_referenced_node(Ref(assignee_ref[:-1]), ctx)
        if provided_unit := self._try_get_unit_from_type_info(ctx.type_info()):
            assignee = self._ensure_param(target, assignee_ref[-1], provided_unit, ctx)
        else:
            assignee = self._get_or_promise_param(target, assignee_ref[-1], ctx)

        value = self.visitCum_assignable(ctx.cum_assignable())

        # HACK: we have no way to check by what operator
        # the param is dynamically resolved
        # For now we assume any dynamic trait is sufficient
        if ctx.cum_operator().ADD_ASSIGN():
            assignee.alias_is(value)
        elif ctx.cum_operator().SUB_ASSIGN():
            assignee.alias_is(-value)
        else:
            # Syntax should protect from this
            raise ValueError(f"Unhandled set assignment operator {ctx}")

        with downgrade(DeprecatedException), self._suppressor_visitCum_assign_stmt:
            raise DeprecatedException(f"{ctx.cum_operator().getText()} is deprecated.")
        return NOTHING

    # TODO: @v0.4 remove this deprecated import form
    _suppressor_visitSet_assign_stmt = suppress_after_count(
        3,
        DeprecatedException,
        logger=logger,
        suppression_warning="Suppressing further deprecation warnings",
    )

    def visitSet_assign_stmt(self, ctx: ap.Set_assign_stmtContext):
        """
        Set cumulative assignments can only be made on top of
        nothing (implicitly declared) or declared, but undefined values.

        Unlike assignments, they may not implicitly declare an attribute.
        """
        assignee_ref = self.visitName_or_attr(ctx.name_or_attr())
        target = self._get_referenced_node(Ref(assignee_ref[:-1]), ctx)
        if provided_unit := self._try_get_unit_from_type_info(ctx.type_info()):
            assignee = self._ensure_param(target, assignee_ref[-1], provided_unit, ctx)
        else:
            assignee = self._get_or_promise_param(target, assignee_ref[-1], ctx)

        value = self.visitCum_assignable(ctx.cum_assignable())

        if ctx.OR_ASSIGN():
            assignee.constrain_superset(value)
        elif ctx.AND_ASSIGN():
            assignee.constrain_subset(value)
        else:
            # Syntax should protect from this
            raise ValueError(f"Unhandled set assignment operator {ctx}")

        with downgrade(DeprecatedException), self._suppressor_visitSet_assign_stmt:
            if ctx.OR_ASSIGN():
                subset = ctx.cum_assignable().getText()
                superset = ctx.name_or_attr().getText()
            else:
                subset = ctx.name_or_attr().getText()
                superset = ctx.cum_assignable().getText()
            raise DeprecatedException(
                f"Set assignment of `{assignee}` is deprecated."
                f' Use "assert `{subset}` within `{superset}` "instead.'
            )
        return NOTHING

    def _try_get_unit_from_type_info(
        self, ctx: ap.Type_infoContext | None
    ) -> UnitType | None:
        if ctx is None:
            return None
        unit_ctx: ap.Name_or_attrContext = ctx.name_or_attr()
        # TODO: @v0.4.0: remove this shim
        unit_ref = self.visitName_or_attr(unit_ctx)
        if len(unit_ref) == 1 and unit_ref[0] in _declaration_domain_to_unit:
            unit = _declaration_domain_to_unit[unit_ref[0]]
            # TODO: consider deprecating this
        else:
            unit = self._get_unit_from_ctx(ctx.name_or_attr())
        return unit

    # TODO: @v0.4 remove this deprecated import form
    _suppressor_visitDeclaration_stmt = suppress_after_count(
        3,
        errors.UserKeyError,
        logger=logger,
        suppression_warning="Suppressing further warnings of this type",
    )

    def visitDeclaration_stmt(self, ctx: ap.Declaration_stmtContext):
        """Handle declaration statements."""
        assigned_value_ref = self.visitName_or_attr(ctx.name_or_attr())
        if len(assigned_value_ref) > 1:
            raise errors.UserSyntaxError.from_ctx(
                ctx,
                f"Can't declare fields in a nested object `{assigned_value_ref}`",
                traceback=self.get_traceback(),
            )

        assigned_name = assigned_value_ref[0]
        unit = self._try_get_unit_from_type_info(ctx.type_info())
        assert unit is not None, "Type info should be enforced by the parser"

        param = self._ensure_param(self._current_node, assigned_name, unit, ctx)
        if param in self._param_assignments:
            with downgrade(errors.UserKeyError), self._suppressor_visitDeclaration_stmt:
                raise errors.UserKeyError.from_ctx(
                    ctx,
                    f"Ignoring declaration of `{assigned_name}` "
                    "because it's already defined",
                    traceback=self.get_traceback(),
                )
        else:
            self._param_assignments[param] = (None, ctx, self.get_traceback())

        return NOTHING

    def visitPass_stmt(self, ctx: ap.Pass_stmtContext):
        return NOTHING


bob = Bob()

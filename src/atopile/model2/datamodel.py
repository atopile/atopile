"""
This datamodel represents the code in a clean, simple and traversable way,
but doesn't resolve names of things.
In building this datamodel, we check for name collisions, but we don't resolve them yet.
"""
import logging
from functools import partial
from typing import Any, Mapping, Optional, Iterable, Type

from antlr4 import ParserRuleContext
from attrs import define, field, resolve_types

from .datatypes import KeyOptMap, Ref


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)



@define
class Link:
    """Represent a connection between two connectable things."""

    source_ref: Ref
    target_ref: Ref
    src_ctx: Optional[ParserRuleContext] = None

    source_obj: Optional["Object"] = None
    target_obj: Optional["Object"] = None
    source_node: Optional["Object"] = None
    target_node: Optional["Object"] = None


@define
class Replace:
    """Represent a replacement of one object with another."""

    original_ref: Ref
    replacement_ref: Ref
    src_ctx: Optional[ParserRuleContext] = None

    # FIXME: I haven't finished planning how to represent this yet


@define
class Import:
    """Represent an import statement."""

    what_ref: Ref
    from_name: str
    src_ctx: Optional[ParserRuleContext] = None

    what_obj: Optional["Object"] = None


@define
class Object:
    """Represent a container class."""

    supers_refs: tuple[Ref]
    locals_: KeyOptMap
    src_ctx: Optional[ParserRuleContext] = None

    # these are a shortcut to the named locals - they're the same thing
    # this is here purely for efficiency
    named_locals: Mapping[Ref, Any] = field(init=False)
    unnamed_locals: Iterable[Any] = field(init=False)
    locals_by_type: Mapping[Type, tuple[Ref, Any]] = field(init=False)

    # configured post-construction
    closure: Optional[tuple["Object"]] = None

    supers_objs: Optional[tuple["Object"]] = None

    def __attrs_post_init__(self) -> None:
        """Set up the shortcuts to locals."""
        self.named_locals = self.locals_.named_items()
        self.unnamed_locals = tuple(self.locals_.unnamed_items())  # cast to tuple because otherwise it's lazy
        self.locals_by_type = self.locals_.map_items_by_type((Link, Replace, Import, Object))


resolve_types(Link)
resolve_types(Replace)
resolve_types(Import)
resolve_types(Object)


# these are the build-in superclasses that have special meaning to the compiler
MODULE = (Ref.from_one("module"),)
COMPONENT = (Ref.from_one("component"),)

PIN = (Ref.from_one("pin"),)
SIGNAL = (Ref.from_one("signal"),)
INTERFACE = (Ref.from_one("interface"),)


root_object = partial(Object, supers_refs=(), locals_=KeyOptMap(()), closure=())
BUILTINS = {
    MODULE: root_object(),
    COMPONENT: root_object(),
    PIN: root_object(),
    SIGNAL: root_object(),
    INTERFACE: root_object(),
}

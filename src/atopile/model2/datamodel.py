"""
This datamodel represents the code in a clean, simple and traversable way,
but doesn't resolve names of things.
In building this datamodel, we check for name collisions, but we don't resolve them yet.
"""
from collections import ChainMap
from functools import partial
from typing import Any, Iterable, Mapping, Optional, Type

from antlr4 import ParserRuleContext
from attrs import define, field, resolve_types

from atopile.address import AddrStr
from atopile.model2.datatypes import Ref, KeyOptMap


@define
class Base:
    """Represent a base class for all things."""
    src_ctx: Optional[ParserRuleContext] = field(kw_only=True, default=None)
    errors: list[Exception] = field(kw_only=True, factory=list)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


@define(repr=False)
class Link(Base):
    """Represent a connection between two connectable things."""
    source_ref: Ref
    target_ref: Ref

    def __repr__(self) -> str:
        return super().__repr__() + f" {self.source_ref} -> {self.target_ref}"


@define(repr=False)
class Replace(Base):
    """Represent a replacement of one object with another."""
    original_ref: Ref
    replacement_ref: Ref

    replacement_obj: Optional["Object"] = None


@define(repr=False)
class Import(Base):
    """Represent an import statement."""
    what_ref: Ref
    from_name: str

    what_obj: Optional["Object"] = None


@define(repr=False)
class Object(Base):
    """Represent a container class."""
    supers_refs: tuple[Ref]
    locals_: KeyOptMap

    # these are a shortcut to the named locals - they're the same thing
    # this is here purely for efficiency
    named_locals: Mapping[Ref, Any] = field(init=False)
    unnamed_locals: Iterable[Any] = field(init=False)
    locals_by_type: Mapping[Type, Iterable[tuple[Ref, Any]]] = field(init=False)

    # configured post-construction
    closure: Optional[tuple["Object"]] = None
    address: Optional[AddrStr] = None

    supers_objs: Optional[tuple["Object"]] = None
    supers_bfs: Optional[tuple["Object"]] = None

    def __attrs_post_init__(self) -> None:
        """Set up the shortcuts to locals."""
        self.named_locals = self.locals_.named_items()
        self.unnamed_locals = tuple(self.locals_.unnamed_items())  # cast to tuple because otherwise it's lazy
        self.locals_by_type = self.locals_.map_items_by_type((Link, Replace, Import, Object, (str, int)))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.address}>"


resolve_types(Link)
resolve_types(Replace)
resolve_types(Import)
resolve_types(Object)


# these are the build-in superclasses that have special meaning to the compiler
MODULE_REF = Ref.from_one("module")
COMPONENT_REF = Ref.from_one("component")
PIN_REF = Ref.from_one("pin")
SIGNAL_REF = Ref.from_one("signal")
INTERFACE_REF = Ref.from_one("interface")


root_object = partial(Object, supers_refs=(), locals_=KeyOptMap(()), closure=())
MODULE = root_object(address=AddrStr("<Built-in> Module"))
COMPONENT = Object(supers_refs=(MODULE_REF,), locals_=KeyOptMap(()), closure=())
PIN = root_object(address=AddrStr("<Built-in> Pin"))
SIGNAL = root_object(address=AddrStr("<Built-in> Signal"))
INTERFACE = root_object(address=AddrStr("<Built-in> Interface"))

BUILTINS = {
    MODULE_REF: MODULE,
    COMPONENT_REF: COMPONENT,
    PIN_REF: PIN,
    SIGNAL_REF: SIGNAL,
    INTERFACE_REF: INTERFACE,
}


## The below datastructures are created from the above datamodel as a second stage


@define
class Joint:
    """Represent a connection between two connectable things."""
    origin_link: Link

    contained_by: "Instance"
    source_connected: "Instance"
    target_connected: "Instance"

    source: "Instance"
    target: "Instance"

    def __repr__(self) -> str:
        return f"<Joint {repr(self.source)} -> {repr(self.target)}>"


@define
class Instance:
    """Represent a concrete object class."""
    ref: Ref

    origin: Optional[Object] = None

    children_from_classes: dict[str, Any] = field(factory=dict)
    children_from_mods: dict[str, Any] = field(factory=dict)

    joints: list[Joint] = field(factory=list)
    joined_to_me: list[Joint] = field(factory=list)

    parent: Optional["Instance"] = None
    children: ChainMap[str, Any] = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.children = ChainMap(self.children_from_mods, self.children_from_classes)

    def __repr__(self) -> str:
        return f"<Instance {self.ref}>"


resolve_types(Joint)
resolve_types(Instance)

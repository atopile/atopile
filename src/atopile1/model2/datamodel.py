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


# @define(repr=False)
# class Link(Base):
#     """Represent a connection between two connectable things."""
#     source_ref: Ref
#     target_ref: Ref

#     def __repr__(self) -> str:
#         return super().__repr__() + f" {self.source_ref} -> {self.target_ref}"


@define(repr=False)
class Import(Base):
    """Represent an import statement."""
    obj_addr: AddrStr

    def __repr__(self) -> str:
        return f"<Import {self.obj_addr}>"


@define
class Replacement(Base):
    """Represent a replacement statement."""
    new_super_ref: Ref

    def __repr__(self) -> str:
        return f"<Replacement {self.new_super_ref}>"


@define(repr=False)
class ObjectDef(Base):
    """
    Represent the definition or skeleton of an object
    so we know where we can go to find the object later
    without actually building the whole file.

    This is mainly because we don't want to hit errors that
    aren't relevant to the current build - instead leaving them
    to be hit in the case we're actually building that object.
    """
    super_ref: Optional[Ref]
    imports: Mapping[Ref, Import]

    local_defs: Mapping[Ref, "ObjectDef"]
    replacements: Mapping[Ref, Replacement]

    # attached immediately to the object post construction
    closure: Optional[tuple["ObjectDef"]] = None # in order of lookup
    address: Optional[AddrStr] = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.address}>"


@define(repr=False)
class ObjectLayer(Base):
    """
    Represent a layer in the object hierarchy.
    This holds all the values assigned to the object.
    """
    # information about where this object is found in multiple forms
    # this is redundant with one another (eg. you can compute one from the other)
    # but it's useful to have all of them for different purposes
    obj_def: ObjectDef

    # None indicates that this is a root object
    super: Optional["ObjectLayer"]

    # the local objects and vars are things we navigate to a lot
    # objs: Optional[Mapping[str, "Object"]] = None
    data: Optional[Mapping[str, Any]] = None

    # data from the lock-file entry associated with this object
    # lock_data: Mapping[str, Any] = {}  # TODO: this should point to a lockfile entry

    @property
    def address(self) -> AddrStr:
        return self.obj_def.address

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.obj_def.address}>"


resolve_types(ObjectLayer)


## The below datastructures are created from the above datamodel as a second stage


@define
class LinkDef(Base):
    """
    Represent a connection between two connectable things.

    # TODO: we may not need this using loop-soup
    # the reason this currently exists is to allow us to map joints between instances
    # these make sense only in the context of the pins and signals, which aren't
    # language fundamentals as much as net objects - eg. they're useful only from
    # a specific electrical perspective
    # origin_link: Link
    """
    source: Ref
    target: Ref

    def __repr__(self) -> str:
        return f"<LinkDef {repr(self.source)} -> {repr(self.target)}>"


@define
class Link(Base):
    """Represent a connection between two connectable things."""
    # TODO: we may not need this using loop-soup
    # the reason this currently exists is to allow us to map joints between instances
    # these make sense only in the context of the pins and signals, which aren't
    # language fundamentals as much as net objects - eg. they're useful only from
    # a specific electrical perspective
    # origin_link: Link

    parent: "Instance"
    source: "Instance"
    target: "Instance"

    def __repr__(self) -> str:
        return f"<Link {repr(self.source)} -> {repr(self.target)}>"


@define
class Instance(Base):
    """
    Represents the specific instance, capturing, the story you told of
    how to get there in it's mapping stacks.
    """
    # origin information
    # much of this information is redundant, however it's all highly referenced
    # so it's useful to have it all at hand
    ref: Ref
    supers: tuple["ObjectLayer"]
    children: dict[str, "Instance"]
    links: list[Link]

    data: Mapping[str, Any]  # this is a chainmap inheriting from the supers as well

    override_data: dict[str, Any]
    _override_location: dict[str, ObjectLayer] = {}  # FIXME: this is a hack to define it here

    # TODO: for later
    # lock_data: Optional[Mapping[str, Any]] = None

    # attached immediately after construction
    parents: Optional[tuple["Instance"]] = None

    def __repr__(self) -> str:
        return f"<Instance {self.ref}>"


resolve_types(LinkDef)
resolve_types(Instance)
resolve_types(Link)

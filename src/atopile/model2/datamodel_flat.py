"""
This datamodel represents the circuit from a specific point of view - eg. through a certain path.
It's entirely invalidated when the circuit changes at all and needs to be rebuilt.
"""
import logging
from typing import Any, Optional

from attrs import define, resolve_types

from . import datamodel as dm1


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@define
class Link:
    """Represent a connection between two connectable things."""
    origin_link: dm1.Link

    origin_instance: "Instance"
    source: "Instance"
    target: "Instance"


@define
class Instance:
    """Represent a concrete object class."""
    path: tuple[str]
    class_: dm1.Object

    parent: Optional["Instance"]
    children: dict[str, Any | "Instance"]

    links: tuple[Link]
    linked_to_me: tuple[Link]


resolve_types(Link)
resolve_types(Instance)

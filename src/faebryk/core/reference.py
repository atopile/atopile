from collections import defaultdict
from typing import cast

from faebryk.core.graphinterface import (
    GraphInterfaceReference,
    GraphInterfaceReferenceUnboundError,
)
from faebryk.core.link import LinkPointer
from faebryk.core.node import Node, constructed_field


class Reference[O: Node](constructed_field):
    """
    Create a simple reference to other nodes that are properly encoded in the graph.
    """

    class UnboundError(Exception):
        """Cannot resolve unbound reference"""

    def __init__(self, out_type: type[O] | None = None):
        self.gifs: dict[Node, GraphInterfaceReference] = defaultdict(
            GraphInterfaceReference
        )
        self.is_set: set[Node] = set()

        def get(instance: Node) -> O:
            try:
                return cast(O, self.gifs[instance].get_reference())
            except GraphInterfaceReferenceUnboundError as ex:
                raise Reference.UnboundError from ex

        def set_(instance: Node, value: O):
            if instance in self.is_set:
                # TypeError is also raised when attempting to assign
                # to an immutable (eg. tuple)
                raise TypeError(
                    f"{self.__class__.__name__} already set and are immutable"
                )
            self.is_set.add(instance)

            if out_type is not None and not isinstance(value, out_type):
                raise TypeError(f"Expected {out_type} got {type(value)}")

            # attach our gif to what we're referring to
            self.gifs[instance].connect(value.self_gif, LinkPointer())

        property.__init__(self, get, set_)

    def __construct__(self, obj: Node) -> None:
        # add our gif to our instance object
        obj.add(self.gifs[obj])

        # don't attach anything additional to the Node during field setup
        return None


def reference[O: Node](out_type: type[O] | None = None) -> O | Reference:
    """
    Create a simple reference to other nodes properly encoded in the graph.

    This final wrapper is primarily to fudge the typing.
    """
    return Reference(out_type=out_type)

from abc import abstractmethod

from faebryk.core.node import Node


class Layout:
    @abstractmethod
    def apply(self, *node: Node): ...

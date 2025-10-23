from abc import abstractmethod

import faebryk.core.node as fabll


class Layout:
    @abstractmethod
    def apply(self, *node: fabll.Node): ...

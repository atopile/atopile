from faebryk.core.node import Node
from faebryk.core.reference import Reference
from faebryk.core.trait import Trait


class has_reference(Trait):
    """Trait-attached reference"""

    reference = Reference()

    def __init__(self, reference: Node):
        super().__init__()
        self.reference = reference

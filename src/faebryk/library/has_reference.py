import faebryk.core.node as fabll
from faebryk.core.reference import Reference
from faebryk.core.trait import Trait


class has_reference(Trait):
    """Trait-attached reference"""

    reference = Reference()

    def __init__(self, reference: fabll.Node):
        super().__init__()
        self.reference = reference

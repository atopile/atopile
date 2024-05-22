import logging
from enum import Enum, auto

from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint_symmetrically import (
    can_attach_to_footprint_symmetrically,
)
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import (
    has_designator_prefix_defined,
)
from faebryk.library.TBD import TBD
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class Fuse(Module):
    class FuseType(Enum):
        NON_RESETTABLE = auto()
        RESETTABLE = auto()

    class ResponseType(Enum):
        SLOW = auto()
        FAST = auto()

    def __init__(self):
        super().__init__()

        class _IFs(Module.IFS()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()):
            fuse_type = TBD[Fuse.FuseType]()
            response_type = TBD[Fuse.ResponseType]()
            trip_current = TBD[float]()

        self.PARAMs = _PARAMs(self)

        self.add_trait(can_attach_to_footprint_symmetrically())
        self.add_trait(can_bridge_defined(self.IFs.unnamed[0], self.IFs.unnamed[1]))
        self.add_trait(has_designator_prefix_defined("F"))

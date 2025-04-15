import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.library.implements_design_check import CheckException
from faebryk.libs.library import L


class RequiresPullNotFulfilled(CheckException):
    def __init__(self, nodes: list[F.ElectricSignal]):
        self.nodes = nodes
        super().__init__(
            f"Signals requiring pulls but not pulled: "
            f"{', '.join(mif.get_full_name() for mif in nodes)}"
        )


class requires_pulls(Module.TraitT.decless()):
    def __init__(self, *logics: F.ElectricSignal):
        super().__init__()

        # TODO: direction, magnitude
        self.logics = logics

    @L.rt_field
    def check(self) -> F.implements_design_check:
        def _check():
            unfulfilled = [
                logic
                for logic in self.logics
                if (is_pulled := logic.try_get_trait(F.is_pulled)) is None
                or not is_pulled.check()
            ]

            if unfulfilled:
                raise RequiresPullNotFulfilled(unfulfilled)

        return F.implements_design_check(_check)

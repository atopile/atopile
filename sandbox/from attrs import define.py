from attrs import define
from atopile.expressions import RangedValue

@define
class AtoType:
    assertions: list

    def connect(other: "AtoType") -> "AtoType":
        raise NotImplementedError

    def check(self) -> bool:
        raise NotImplementedError


@define
class PowerSourceInterface(AtoType):
    operating_voltage: RangedValue
    current: RangedValue

    def combine(self, other: "PowerSourceInterface") -> "PowerSourceInterface":
        # check whether this combination is valid
        super().combine(other)

        # combine attributes
        return PowerSourceInterface(
            operating_voltage = self.operating_voltage | other.operating_voltage,
            current = self.current + other.current
        )

    def check(self) -> bool:
        return self.power >= 0

    def __repr__(self):
        return f"PowerInterface({self.power})"
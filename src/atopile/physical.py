import pint
from attrs import define

@define
class Variable:
    """Let's get physical!"""
    unit: pint.Unit
    nominal: float
    tolerance_factor: float

    def __repr__(self) -> str:
        return f"<Variable {self.nominal} +/- {self.tolerance_factor * self.nominal} {self.unit}>"

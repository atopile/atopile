from pydantic import BaseModel, model_validator, ValidationError, ValidationInfo, validator

from typing import Type
from typing_extensions import Self

from atopile.front_end import RangedValue, Instance

from atopile import errors


class DBRangedValue(BaseModel):
    unit: str
    min: float
    max: float

    @staticmethod
    def from_ranged_value(value: RangedValue) -> "DBRangedValue":
        return DBRangedValue(unit=str(value.unit), min=value.min_val, max=value.max_val)

class DBComponent(BaseModel):
    """
    A standard inductor that gets sent to the server
    """
    value: DBRangedValue|None = None
    package: str|None = None
    footprint: str|None = None
    mpn: str|None = None
    status: str|None = None

    @model_validator(mode='after')
    def check_package_footprint(self) -> Self:
        package = self.package
        footprint = self.footprint
        if package is None and footprint is None:
            #FIXME: how do I know which component in the error message?
            raise errors.AtoError('need package or footprint for component')
        return self

    class Config:
        # User might provide extra fields but we ignore those when sending them to the server
        extra = "ignore"

class Resistor(DBComponent):
    """
    A standard resistor that gets sent to the server
    """
    resistance: DBRangedValue|None = None

    @validator('resistance', always=True)
    def check_resistance_or_value(cls, resistance, values):
        """
        Ensure either resistance or value is set. If only value is set, transfer it to resistance.
        """
        if resistance is None and 'value' in values and values['value'] is not None:
            resistance = values['value']
            if values['value'].unit != 'ohm':
                raise ValueError("Unit for resistance must be 'ohm'")
        elif resistance is None:
            raise ValueError("Either resistance or value must be set for a Resistor.")
        return resistance

class Capacitor(DBComponent):
    """
    A standard capacitor that gets sent to the server
    """
    capacitance: DBRangedValue|None = None

class Inductor(DBComponent):
    """
    A standard inductor that gets sent to the server
    """
    inductance: DBRangedValue|None = None
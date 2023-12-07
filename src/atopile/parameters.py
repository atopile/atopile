from attr import define
from atopile.instance_methods import get_parent, get_name
from numbers import Number
from atopile.instance_methods import get_data_dict


@define
class Parameter:
    """TODO:"""

    min: float
    max: float
    unit: str


DEFAULT_TOLERANCE = 0.01  # 1%


def get_parameter(addr: str) -> Parameter:
    """Return a parameter for a given address."""
    # if we know what do to solve this param, do it
    # TODO: we currently don't know how to solve for parameters

    # otherwise, make a parameter representing the value the user has assigned
    # first check that the addr's parent exists
    parent = get_parent(addr)
    if not parent:
        raise ValueError("Cannot make a parameter from the root")

    spec = get_data_dict(parent)[get_name(addr)]

    if spec == "UNKNOWN":
        raise ValueError("Parameter doesn't have a known value")

    if not isinstance(spec, Number):
        raise ValueError("Cannot make a parameter from a string")

    return Parameter(
        min=spec * (1 - DEFAULT_TOLERANCE),
        max=spec * (1 + DEFAULT_TOLERANCE),
        unit="",  # TODO:
    )

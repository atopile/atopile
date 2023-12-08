from numbers import Number

from attr import define

from atopile.address import AddrStr
from atopile import address
from atopile.instance_methods import get_data_dict, get_name, get_parent
from atopile.equations import EquationBuilder


@define
class Parameter:
    """TODO:"""

    min: float
    max: float
    unit: str


DEFAULT_TOLERANCE = 0.01  # 1%


_known_values: dict[AddrStr, Number] = {}
_eqn_builder = EquationBuilder()


def get_parameter(addr: str) -> Parameter:
    """Return a parameter for a given address."""
    # if we know what do to solve this param, do it
    # TODO: we currently don't know how to solve for parameters

    if not _known_values:
        root = address.get_entry(addr)
        _eqn_builder.build(root)

        unknowns = []
        for addr in _eqn_builder._symbols:
            parent = get_parent(addr)
            data_dict = get_data_dict(parent)
            value = data_dict[get_name(addr)]
            if isinstance(value, Number):
                _known_values[addr] = value
            else:
                unknowns.append(addr)

        _known_values.update(_eqn_builder.solve(_known_values, unknowns))

    # otherwise, make a parameter representing the value the user has assigned
    # first check that the addr's parent exists
    parent = get_parent(addr)
    if not parent:
        raise ValueError("Cannot make a parameter from the root")

    spec = get_data_dict(parent)[get_name(addr)]

    if spec == "UNKNOWN":
        try:
            value = _known_values[addr]
        except KeyError:
            raise ValueError("No value available for this parameter")
    elif isinstance(spec, Number):
        value = spec
    else:
        raise ValueError("Cannot make a parameter from a string")

    return Parameter(
        min=value * (1 - DEFAULT_TOLERANCE),
        max=value * (1 + DEFAULT_TOLERANCE),
        unit="",  # TODO:
    )

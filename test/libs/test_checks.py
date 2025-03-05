import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.app.checks import (
    UnspecifiedParameterError,
    check_parameters,
)
from faebryk.libs.library import L


def test_unspecified_parameter():
    class App(Module):
        p = L.p_field()

    app = App()
    app.add(F.has_descriptive_properties_defined({"LCSC": "C2024"}))

    G = app.get_graph()
    params = app.get_children(False, types=Parameter)

    solver = DefaultSolver()
    solver.simplify(app)
    check_parameters(params, G, solver)

    app.p.constrain_subset(L.Range(2.5, 4.2))
    solver.simplify(app)
    with pytest.raises(UnspecifiedParameterError):
        check_parameters(params, G, solver)

    app.p.alias_is(L.Range.from_center_rel(3.3, 0.1))
    solver.simplify(app)
    check_parameters(params, G, solver)

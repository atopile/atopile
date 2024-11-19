# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from enum import Enum

import pytest

from faebryk.core.parameter import ParameterOperableHasNoLiteral
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


def test_repr_chain_basic():
    import faebryk.library._F as F

    class TestModule(L.Module):
        param1 = L.p_field(units=P.V)
        param2 = L.p_field(units=P.A)
        param3 = L.p_field(units=P.V)

        @L.rt_field
        def simple_value_representation(self):
            S = F.has_simple_value_representation_based_on_params_chain.Spec
            return F.has_simple_value_representation_based_on_params_chain(
                S(param=self.param1, tolerance=True),
                S(param=self.param2, suffix="P2"),
                S(param=self.param3, tolerance=True, suffix="P3"),
                prefix="TM",
            )

    m = TestModule()
    m.param1.alias_is(L.Range(10 * P.V, 20 * P.V))
    m.param2.alias_is(5 * P.A)
    m.param3.alias_is(10 * P.V)

    val = m.get_trait(F.has_simple_value_representation).get_value()
    assert val == "TM 15V ±33% 5A P2 10V P3"


def test_repr_chain_non_number():
    import faebryk.library._F as F

    class TestEnum(Enum):
        A = "AS"
        B = "BS"

    class TestModule(L.Module):
        param1 = L.p_field(domain=L.Domains.ENUM(TestEnum))
        param2 = L.p_field(domain=L.Domains.BOOL())

        @L.rt_field
        def simple_value_representation(self):
            S = F.has_simple_value_representation_based_on_params_chain.Spec
            return F.has_simple_value_representation_based_on_params_chain(
                S(param=self.param1),
                S(param=self.param2, prefix="P2:"),
            )

    m = TestModule()
    m.param1.alias_is(TestEnum.A)
    m.param2.alias_is(True)

    val = m.get_trait(F.has_simple_value_representation).get_value()
    assert val == "AS P2: true"


def test_repr_chain_no_literal():
    import faebryk.library._F as F

    class TestModule(L.Module):
        param1 = L.p_field(units=P.V)
        param2 = L.p_field(units=P.A)
        param3 = L.p_field(units=P.V)

        @L.rt_field
        def simple_value_representation(self):
            S = F.has_simple_value_representation_based_on_params_chain.Spec
            return F.has_simple_value_representation_based_on_params_chain(
                S(param=self.param1, default=None),
                S(param=self.param2),
                S(param=self.param3, default="P3: MISSING"),
            )

    m = TestModule()

    pytest.raises(
        ParameterOperableHasNoLiteral,
        m.get_trait(F.has_simple_value_representation).get_value,
    )

    m.param1.alias_is(10 * P.V)
    val = m.get_trait(F.has_simple_value_representation).get_value()
    assert val == "10V P3: MISSING"

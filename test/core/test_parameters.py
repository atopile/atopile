# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import unittest
from operator import add
from typing import TypeVar

from faebryk.core.core import Module, Parameter
from faebryk.core.core import logger as core_logger
from faebryk.library.ANY import ANY
from faebryk.library.Constant import Constant
from faebryk.library.Operation import Operation
from faebryk.library.Range import Range
from faebryk.library.Resistor import Resistor
from faebryk.library.Set import Set
from faebryk.library.TBD import TBD
from faebryk.library.UART_Base import UART_Base
from faebryk.libs.units import P

logger = logging.getLogger(__name__)
core_logger.setLevel(logger.getEffectiveLevel())


class TestParameters(unittest.TestCase):
    def test_operations(self):
        def assertIsInstance[T: Parameter](obj: Parameter, cls: type[T]) -> T:
            obj = obj.get_most_narrow()
            self.assertIsInstance(obj, cls)
            assert isinstance(obj, cls)
            return obj

        # Constant
        ONE = Constant(1)
        self.assertEqual(ONE.value, 1)

        TWO = Constant(2)
        self.assertEqual(assertIsInstance(ONE + TWO, Constant).value, 3)
        self.assertEqual(assertIsInstance(ONE - TWO, Constant).value, -1)

        self.assertEqual(assertIsInstance((ONE / TWO) / TWO, Constant).value, 1 / 4)

        # Range
        R_ONE_TEN = Range(1, 10)
        self.assertEqual(assertIsInstance(R_ONE_TEN + TWO, Range), Range(3, 12))

        R_TWO_THREE = Range(2, 3)
        self.assertEqual(assertIsInstance(R_ONE_TEN + R_TWO_THREE, Range), Range(3, 13))
        self.assertEqual(assertIsInstance(R_ONE_TEN * R_TWO_THREE, Range), Range(2, 30))
        self.assertEqual(assertIsInstance(R_ONE_TEN - R_TWO_THREE, Range), Range(-2, 8))
        self.assertEqual(
            assertIsInstance(R_ONE_TEN / R_TWO_THREE, Range), Range(1 / 3, 10 / 2)
        )

        # TBD Range
        a = TBD[int]()
        b = TBD[int]()
        R_TBD = Range(a, b)
        add = R_ONE_TEN + R_TBD
        mul = R_ONE_TEN * R_TBD
        sub = R_ONE_TEN - R_TBD
        div = R_ONE_TEN / R_TBD
        a.merge(Constant(2))
        b.merge(Constant(3))
        self.assertEqual(assertIsInstance(add, Range), Range(3, 13))
        self.assertEqual(assertIsInstance(mul, Range), Range(2, 30))
        self.assertEqual(assertIsInstance(sub, Range), Range(-2, 8))
        self.assertEqual(assertIsInstance(div, Range), Range(1 / 3, 10 / 2))

        # Set
        S_FIVE_NINE = Set(set(Constant(x) for x in range(5, 10)))
        self.assertEqual(
            assertIsInstance(S_FIVE_NINE + ONE, Set).params,
            set(Constant(x) for x in range(6, 11)),
        )

        S_TEN_TWENTY_THIRTY = Set(set(Constant(x) for x in [10, 20, 30]))
        self.assertEqual(
            assertIsInstance(S_FIVE_NINE + S_TEN_TWENTY_THIRTY, Set),
            Set(Constant(x + y) for x in range(5, 10) for y in [10, 20, 30]),
        )

        # conjunctions
        # with static values
        R_ONE_TEN = Range(1, 10)
        R_TWO_THREE = Range(2, 3)
        self.assertEqual(R_ONE_TEN & R_TWO_THREE, Range(2, 3))
        self.assertEqual(R_ONE_TEN & Range(5, 20), Range(5, 10))
        self.assertEqual(R_ONE_TEN & 5, Constant(5))
        self.assertEqual(R_ONE_TEN & Constant(5), Constant(5))
        self.assertEqual(R_ONE_TEN & Set([1, 5, 8, 12]), Set([1, 5, 8]))
        self.assertEqual(Set([1, 2, 3]) & Set([2, 3, 4]), Set([2, 3]))
        self.assertEqual(Set([1, 2, 3]) & 3, Constant(3))
        self.assertEqual(Constant(3) & 3, Constant(3))
        self.assertEqual(Constant(2) & 3, Set([]))
        self.assertEqual(R_ONE_TEN & [1, 2, 11], Set([1, 2]))
        # with tbd
        a = TBD[int]()
        b = TBD[int]()
        R_TBD = Range(a, b)
        r_one_ten_con_tbd = R_ONE_TEN & R_TBD
        assertIsInstance(r_one_ten_con_tbd, Operation)
        a.merge(2)
        b.merge(20)
        self.assertEqual(assertIsInstance(r_one_ten_con_tbd, Range), Range(2, 10))

        # TODO disjunctions

        # Operation
        token = TBD()
        op = assertIsInstance(ONE + token, Operation)
        op2 = assertIsInstance(op + 10, Operation)

        self.assertEqual(op.operands, (ONE, TBD()))
        self.assertEqual(op.operation(1, 2), 3)

        token.merge(Constant(2))
        self.assertEqual(op.get_most_narrow(), Constant(3))

        self.assertEqual(op + 5, Constant(8))
        self.assertEqual(op2.get_most_narrow(), Constant(13))

        # Any
        assertIsInstance(ONE + ANY(), Operation)
        assertIsInstance(TBD() + ANY(), Operation)
        assertIsInstance((TBD() + TBD()) + ANY(), Operation)

        # Test quantities
        self.assertEqual(Constant(1 * P.baud), 1 * P.baud)
        self.assertEqual(Constant(1) * P.baud, 1 * P.baud)
        self.assertEqual(Range(1, 10) * P.baud, Range(1 * P.baud, 10 * P.baud))
        self.assertEqual(Set([1, 2]) * P.baud, Set([1 * P.baud, 2 * P.baud]))

    def test_resolution(self):
        T = TypeVar("T")

        def assertIsInstance(obj, cls: type[T]) -> T:
            self.assertIsInstance(obj, cls)
            assert isinstance(obj, cls)
            return obj

        ONE = Constant(1)
        self.assertEqual(
            assertIsInstance(Parameter.resolve_all([ONE, ONE]), Constant).value, 1
        )

        TWO = Constant(2)
        self.assertEqual(
            assertIsInstance(
                Parameter.resolve_all([Operation([ONE, ONE], add), TWO]), Constant
            ).value,
            2,
        )

        self.assertEqual(TBD(), TBD())
        self.assertEqual(ANY(), ANY())

    def test_modules(self):
        T = TypeVar("T")

        def assertIsInstance(obj, cls: type[T]) -> T:
            self.assertIsInstance(obj, cls)
            assert isinstance(obj, cls)
            return obj

        class Modules(Module):
            def __init__(self) -> None:
                super().__init__()

                class NODES(super().NODES()):
                    UART_A = UART_Base()
                    UART_B = UART_Base()
                    UART_C = UART_Base()

                self.NODEs = NODES(self)

        m = Modules()

        UART_A = m.NODEs.UART_A
        UART_B = m.NODEs.UART_B
        UART_C = m.NODEs.UART_C

        UART_A.connect(UART_B)

        UART_A.PARAMs.baud.merge(Constant(9600 * P.baud))

        for uart in [UART_A, UART_B]:
            self.assertEqual(
                assertIsInstance(uart.PARAMs.baud.get_most_narrow(), Constant).value,
                9600 * P.baud,
            )

        UART_C.PARAMs.baud.merge(Range(1200 * P.baud, 115200 * P.baud))
        UART_A.connect(UART_C)

        for uart in [UART_A, UART_B, UART_C]:
            self.assertEqual(
                assertIsInstance(uart.PARAMs.baud.get_most_narrow(), Constant).value,
                9600 * P.baud,
            )

        resistor = Resistor()

        assertIsInstance(
            resistor.get_current_flow_by_voltage_resistance(Constant(0.5)), Operation
        )

    def test_comparisons(self):
        # same type
        self.assertGreater(Constant(2), Constant(1))
        self.assertLess(Constant(1), Constant(2))
        self.assertLessEqual(Constant(2), Constant(2))
        self.assertGreaterEqual(Constant(2), Constant(2))
        self.assertLess(Range(1, 2), Range(3, 4))
        self.assertEqual(min(Range(1, 2), Range(3, 4), Range(5, 6)), Range(1, 2))

        # mixed
        self.assertLess(Constant(1), Range(2, 3))
        self.assertGreater(Constant(4), Range(2, 3))
        self.assertFalse(Constant(3) < Range(2, 4))
        self.assertFalse(Constant(3) > Range(2, 4))
        self.assertFalse(Constant(3) == Range(2, 4))
        self.assertEqual(min(Constant(3), Range(5, 6), Constant(4)), Constant(3))

        # nested
        self.assertLess(Constant(1), Set([Constant(2), Constant(3)]))
        self.assertLess(Range(1, 2), Range(Constant(3), Constant(4)))
        self.assertLess(Range(1, 2), Set([Constant(4), Constant(3)]))
        self.assertLess(Constant(Constant(Constant(1))), 2)
        self.assertEqual(
            min(Constant(Constant(Constant(1))), Constant(Constant(2))),
            Constant(Constant(Constant(1))),
        )


if __name__ == "__main__":
    unittest.main()

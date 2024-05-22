# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import unittest
from operator import add
from typing import TypeVar

from faebryk.core.core import Module, Parameter
from faebryk.core.core import logger as core_logger
from faebryk.library.Constant import Constant
from faebryk.library.Operation import Operation
from faebryk.library.Range import Range
from faebryk.library.Resistor import Resistor
from faebryk.library.Set import Set
from faebryk.library.TBD import TBD
from faebryk.library.UART_Base import UART_Base

logger = logging.getLogger(__name__)
core_logger.setLevel(logger.getEffectiveLevel())


class TestParameters(unittest.TestCase):
    def test_operations(self):
        T = TypeVar("T")

        def assertIsInstance(obj, cls: type[T]) -> T:
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

        UART_A.PARAMs.baud.merge(Constant(9600))

        for uart in [UART_A, UART_B]:
            self.assertEqual(
                assertIsInstance(uart.PARAMs.baud.get_most_narrow(), Constant).value,
                9600,
            )

        UART_C.PARAMs.baud.merge(Range(1200, 115200))
        UART_A.connect(UART_C)

        for uart in [UART_A, UART_B, UART_C]:
            self.assertEqual(
                assertIsInstance(uart.PARAMs.baud.get_most_narrow(), Constant).value,
                9600,
            )

        resistor = Resistor()

        assertIsInstance(
            resistor.get_current_flow_by_voltage_resistance(Constant(0.5)), Operation
        )


if __name__ == "__main__":
    unittest.main()

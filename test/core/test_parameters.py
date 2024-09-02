# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import unittest
from operator import add

from faebryk.core.core import logger as core_logger
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.core.util import specialize_module
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
        self.assertEqual(R_ONE_TEN & {1, 2, 11}, Set([1, 2]))
        self.assertEqual(R_ONE_TEN & Range(12, 13), Set([]))
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
        def assertIsInstance[T](obj, cls: type[T]) -> T:
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

        def test_merge(
            a: Parameter[int] | set[int] | int | tuple[int, int],
            b: Parameter[int] | set[int] | int | tuple[int, int],
            expected,
        ):
            a = Parameter[int].from_literal(a)
            expected = Parameter[int].from_literal(expected)
            self.assertEqual(a.merge(b), expected)

        def fail_merge(a, b):
            a = Parameter[int].from_literal(a)
            self.assertRaises(Parameter.MergeException, lambda: a.merge(b))

        # Sets ----

        # Ranges
        test_merge((0, 10), (5, 15), (5, 10))
        test_merge((0, 10), (5, 8), (5, 8))
        fail_merge((0, 10), (11, 15))
        test_merge((5, 10), 5, 5)
        fail_merge((0, 10), 11)
        test_merge((5, 10), {5, 6, 12}, {5, 6})

        # Empty set
        fail_merge({1, 2}, set())
        fail_merge((1, 5), set())
        fail_merge(5, set())
        test_merge(set(), set(), set())
        test_merge(TBD(), set(), set())
        test_merge(ANY(), set(), set())

        test_merge({1, 2}, {2, 3}, {2})
        fail_merge({1, 2}, {3, 4})
        test_merge({1, 2}, 2, 2)

        # TBD/ANY --

        test_merge(TBD(), TBD(), TBD())
        test_merge(ANY(), ANY(), ANY())
        test_merge(TBD(), ANY(), ANY())

    def test_specific(self):
        def test_spec(
            a: Parameter[int] | set[int] | int | tuple[int, int],
            b: Parameter[int] | set[int] | int | tuple[int, int],
            expected: bool = True,
        ):
            b = Parameter[int].from_literal(b)
            if expected:
                self.assertTrue(b.is_subset_of(a))
            else:
                self.assertFalse(b.is_subset_of(a))

        test_spec(1, 1)
        test_spec(1, 2, False)

        test_spec((1, 2), 1)
        test_spec(1, (1, 2), False)

        test_spec({1, 2}, 1)
        test_spec(1, {1, 2}, False)
        test_spec(1, {1})

        test_spec((1, 2), (1, 2))
        test_spec((1, 2), (1, 3), False)
        test_spec((1, 10), (1, 3))

        test_spec(1, ANY(), False)
        test_spec(ANY(), 1)
        test_spec(TBD(), 1, False)
        test_spec(ANY(), Operation((1, 2), add))
        test_spec(ANY(), Operation((1, TBD()), add))

        test_spec(Operation((1, 2), add), 3)
        test_spec(Operation((1, TBD()), add), TBD(), False)

    def test_compress(self):
        def test_comp(
            a: Parameter[int].LIT_OR_PARAM,
            expected: Parameter[int].LIT_OR_PARAM,
        ):
            a = Parameter[int].from_literal(a)
            expected = Parameter[int].from_literal(expected)
            self.assertEqual(a.get_most_narrow(), expected)

        test_comp(1, 1)
        test_comp(Constant(Constant(1)), 1)
        test_comp(Constant(Constant(Constant(1))), 1)
        test_comp({1}, 1)
        test_comp(Range(1), 1)
        test_comp(Range(Range(1)), 1)
        test_comp(Constant(Set([Range(Range(1))])), 1)

    def test_modules(self):
        def assertIsInstance[T](obj, cls: type[T]) -> T:
            self.assertIsInstance(obj, cls)
            assert isinstance(obj, cls)
            return obj

        class Modules(Module):
            UART_A: UART_Base
            UART_B: UART_Base
            UART_C: UART_Base

        m = Modules()

        UART_A = m.UART_A
        UART_B = m.UART_B
        UART_C = m.UART_C

        UART_A.connect(UART_B)

        UART_A.baud.merge(Constant(9600 * P.baud))

        for uart in [UART_A, UART_B]:
            self.assertEqual(
                assertIsInstance(uart.baud.get_most_narrow(), Constant).value,
                9600 * P.baud,
            )

        UART_C.baud.merge(Range(1200 * P.baud, 115200 * P.baud))
        UART_A.connect(UART_C)

        for uart in [UART_A, UART_B, UART_C]:
            self.assertEqual(
                assertIsInstance(uart.baud.get_most_narrow(), Constant).value,
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

    def test_specialize(self):
        import faebryk.library._F as F
        from faebryk.libs.brightness import TypicalLuminousIntensity

        for i in range(10):

            class App(Module):
                led: F.PoweredLED
                battery: F.Battery

                def __preinit__(self) -> None:
                    self.led.power.connect(self.battery.power)

                    # Parametrize
                    self.led.led.color.merge(F.LED.Color.YELLOW)
                    self.led.led.brightness.merge(
                        TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value.value
                    )

            app = App()

            bcell = specialize_module(app.battery, F.ButtonCell())
            bcell.voltage.merge(3 * P.V)
            bcell.capacity.merge(Range.from_center(225 * P.mAh, 50 * P.mAh))
            bcell.material.merge(F.ButtonCell.Material.Lithium)
            bcell.size.merge(F.ButtonCell.Size.N_2032)
            bcell.shape.merge(F.ButtonCell.Shape.Round)

            app.led.led.color.merge(F.LED.Color.YELLOW)
            app.led.led.max_brightness.merge(500 * P.millicandela)
            app.led.led.forward_voltage.merge(1.2 * P.V)
            app.led.led.max_current.merge(20 * P.mA)

            v = app.battery.voltage
            # vbcell = bcell.voltage
            # print(pretty_param_tree_top(v))
            # print(pretty_param_tree_top(vbcell))
            self.assertEqual(v.get_most_narrow(), 3 * P.V)
            r = app.led.current_limiting_resistor.resistance
            r = r.get_most_narrow()
            self.assertIsInstance(r, Range, f"{type(r)}")

    def test_units(self):
        self.assertEqual(Constant(1e-9 * P.F), 1 * P.nF)


if __name__ == "__main__":
    unittest.main()

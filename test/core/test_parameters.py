# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import unittest
from operator import add

import faebryk.library._F as F
from faebryk.core.core import logger as core_logger
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
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
        ONE = F.Constant(1)
        self.assertEqual(ONE.value, 1)

        TWO = F.Constant(2)
        self.assertEqual(assertIsInstance(ONE + TWO, F.Constant).value, 3)
        self.assertEqual(assertIsInstance(ONE - TWO, F.Constant).value, -1)

        self.assertEqual(assertIsInstance((ONE / TWO) / TWO, F.Constant).value, 1 / 4)

        # Range
        R_ONE_TEN = F.Range(1, 10)
        self.assertEqual(assertIsInstance(R_ONE_TEN + TWO, F.Range), F.Range(3, 12))

        R_TWO_THREE = F.Range(2, 3)
        self.assertEqual(
            assertIsInstance(R_ONE_TEN + R_TWO_THREE, F.Range), F.Range(3, 13)
        )
        self.assertEqual(
            assertIsInstance(R_ONE_TEN * R_TWO_THREE, F.Range), F.Range(2, 30)
        )
        self.assertEqual(
            assertIsInstance(R_ONE_TEN - R_TWO_THREE, F.Range), F.Range(-2, 8)
        )
        self.assertEqual(
            assertIsInstance(R_ONE_TEN / R_TWO_THREE, F.Range), F.Range(1 / 3, 10 / 2)
        )

        # TBD Range
        a = F.TBD[int]()
        b = F.TBD[int]()
        R_TBD = F.Range(a, b)
        add = R_ONE_TEN + R_TBD
        mul = R_ONE_TEN * R_TBD
        sub = R_ONE_TEN - R_TBD
        div = R_ONE_TEN / R_TBD
        a.merge(F.Constant(2))
        b.merge(F.Constant(3))
        self.assertEqual(assertIsInstance(add, F.Range), F.Range(3, 13))
        self.assertEqual(assertIsInstance(mul, F.Range), F.Range(2, 30))
        self.assertEqual(assertIsInstance(sub, F.Range), F.Range(-2, 8))
        self.assertEqual(assertIsInstance(div, F.Range), F.Range(1 / 3, 10 / 2))

        # Set
        S_FIVE_NINE = F.Set(set(F.Constant(x) for x in range(5, 10)))
        self.assertEqual(
            assertIsInstance(S_FIVE_NINE + ONE, F.Set).params,
            set(F.Constant(x) for x in range(6, 11)),
        )

        S_TEN_TWENTY_THIRTY = F.Set(set(F.Constant(x) for x in [10, 20, 30]))
        self.assertEqual(
            assertIsInstance(S_FIVE_NINE + S_TEN_TWENTY_THIRTY, F.Set),
            F.Set(F.Constant(x + y) for x in range(5, 10) for y in [10, 20, 30]),
        )

        # conjunctions
        # with static values
        R_ONE_TEN = F.Range(1, 10)
        R_TWO_THREE = F.Range(2, 3)
        self.assertEqual(R_ONE_TEN & R_TWO_THREE, F.Range(2, 3))
        self.assertEqual(R_ONE_TEN & F.Range(5, 20), F.Range(5, 10))
        self.assertEqual(R_ONE_TEN & 5, F.Constant(5))
        self.assertEqual(R_ONE_TEN & F.Constant(5), F.Constant(5))
        self.assertEqual(R_ONE_TEN & F.Set([1, 5, 8, 12]), F.Set([1, 5, 8]))
        self.assertEqual(F.Set([1, 2, 3]) & F.Set([2, 3, 4]), F.Set([2, 3]))
        self.assertEqual(F.Set([1, 2, 3]) & 3, F.Constant(3))
        self.assertEqual(F.Constant(3) & 3, F.Constant(3))
        self.assertEqual(F.Constant(2) & 3, F.Set([]))
        self.assertEqual(R_ONE_TEN & {1, 2, 11}, F.Set([1, 2]))
        self.assertEqual(R_ONE_TEN & F.Range(12, 13), F.Set([]))
        # with tbd
        a = F.TBD[int]()
        b = F.TBD[int]()
        RTBD = F.Range(a, b)
        r_one_ten_con_tbd = R_ONE_TEN & RTBD
        assertIsInstance(r_one_ten_con_tbd, F.Operation)
        a.merge(2)
        b.merge(20)
        self.assertEqual(assertIsInstance(r_one_ten_con_tbd, F.Range), F.Range(2, 10))

        # TODO disjunctions

        # F.Operation
        token = F.TBD()
        op = assertIsInstance(ONE + token, F.Operation)
        op2 = assertIsInstance(op + 10, F.Operation)

        self.assertEqual(op.operands, (ONE, F.TBD()))
        self.assertEqual(op.operation(1, 2), 3)

        token.merge(F.Constant(2))
        self.assertEqual(op.get_most_narrow(), F.Constant(3))

        self.assertEqual(op + 5, F.Constant(8))
        self.assertEqual(op2.get_most_narrow(), F.Constant(13))

        # Any
        assertIsInstance(ONE + F.ANY(), F.Operation)
        assertIsInstance(F.TBD() + F.ANY(), F.Operation)
        assertIsInstance((F.TBD() + F.TBD()) + F.ANY(), F.Operation)

        # Test quantities
        self.assertEqual(F.Constant(1 * P.baud), 1 * P.baud)
        self.assertEqual(F.Constant(1) * P.baud, 1 * P.baud)
        self.assertEqual(F.Range(1, 10) * P.baud, F.Range(1 * P.baud, 10 * P.baud))
        self.assertEqual(F.Set([1, 2]) * P.baud, F.Set([1 * P.baud, 2 * P.baud]))

    def test_resolution(self):
        def assertIsInstance[T](obj, cls: type[T]) -> T:
            self.assertIsInstance(obj, cls)
            assert isinstance(obj, cls)
            return obj

        ONE = F.Constant(1)
        self.assertEqual(
            assertIsInstance(Parameter.resolve_all([ONE, ONE]), F.Constant).value, 1
        )

        TWO = F.Constant(2)
        self.assertEqual(
            assertIsInstance(
                Parameter.resolve_all([F.Operation([ONE, ONE], add), TWO]), F.Constant
            ).value,
            2,
        )

        self.assertEqual(F.TBD(), F.TBD())
        self.assertEqual(F.ANY(), F.ANY())

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

        # F.Sets ----

        # F.Ranges
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
        test_merge(F.TBD(), set(), set())
        test_merge(F.ANY(), set(), set())

        test_merge({1, 2}, {2, 3}, {2})
        fail_merge({1, 2}, {3, 4})
        test_merge({1, 2}, 2, 2)

        # F.TBD/F.ANY --

        test_merge(F.TBD(), F.TBD(), F.TBD())
        test_merge(F.ANY(), F.ANY(), F.ANY())
        test_merge(F.TBD(), F.ANY(), F.ANY())

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

        test_spec(1, F.ANY(), False)
        test_spec(F.ANY(), 1)
        test_spec(F.TBD(), 1, False)
        test_spec(F.ANY(), F.Operation((1, 2), add))
        test_spec(F.ANY(), F.Operation((1, F.TBD()), add))

        test_spec(F.Operation((1, 2), add), 3)
        test_spec(F.Operation((1, F.TBD()), add), F.TBD(), False)

    def test_compress(self):
        def test_comp(
            a: Parameter[int].LIT_OR_PARAM,
            expected: Parameter[int].LIT_OR_PARAM,
        ):
            a = Parameter[int].from_literal(a)
            expected = Parameter[int].from_literal(expected)
            self.assertEqual(a.get_most_narrow(), expected)

        test_comp(1, 1)
        test_comp(F.Constant(F.Constant(1)), 1)
        test_comp(F.Constant(F.Constant(F.Constant(1))), 1)
        test_comp({1}, 1)
        test_comp(F.Range(1), 1)
        test_comp(F.Range(F.Range(1)), 1)
        test_comp(F.Constant(F.Set([F.Range(F.Range(1))])), 1)

    def test_modules(self):
        def assertIsInstance[T](obj, cls: type[T]) -> T:
            self.assertIsInstance(obj, cls)
            assert isinstance(obj, cls)
            return obj

        class Modules(Module):
            UART_A: F.UART_Base
            UART_B: F.UART_Base
            UART_C: F.UART_Base

        m = Modules()

        UART_A = m.UART_A
        UART_B = m.UART_B
        UART_C = m.UART_C

        UART_A.connect(UART_B)

        UART_A.baud.merge(F.Constant(9600 * P.baud))

        for uart in [UART_A, UART_B]:
            self.assertEqual(
                assertIsInstance(uart.baud.get_most_narrow(), F.Constant).value,
                9600 * P.baud,
            )

        UART_C.baud.merge(F.Range(1200 * P.baud, 115200 * P.baud))
        UART_A.connect(UART_C)

        for uart in [UART_A, UART_B, UART_C]:
            self.assertEqual(
                assertIsInstance(uart.baud.get_most_narrow(), F.Constant).value,
                9600 * P.baud,
            )

        resistor = F.Resistor()

        assertIsInstance(
            resistor.get_current_flow_by_voltage_resistance(F.Constant(0.5)),
            F.Operation,
        )

    def test_comparisons(self):
        # same type
        self.assertGreater(F.Constant(2), F.Constant(1))
        self.assertLess(F.Constant(1), F.Constant(2))
        self.assertLessEqual(F.Constant(2), F.Constant(2))
        self.assertGreaterEqual(F.Constant(2), F.Constant(2))
        self.assertLess(F.Range(1, 2), F.Range(3, 4))
        self.assertEqual(
            min(F.Range(1, 2), F.Range(3, 4), F.Range(5, 6)), F.Range(1, 2)
        )

        # mixed
        self.assertLess(F.Constant(1), F.Range(2, 3))
        self.assertGreater(F.Constant(4), F.Range(2, 3))
        self.assertFalse(F.Constant(3) < F.Range(2, 4))
        self.assertFalse(F.Constant(3) > F.Range(2, 4))
        self.assertFalse(F.Constant(3) == F.Range(2, 4))
        self.assertEqual(
            min(F.Constant(3), F.Range(5, 6), F.Constant(4)), F.Constant(3)
        )

        # nested
        self.assertLess(F.Constant(1), F.Set([F.Constant(2), F.Constant(3)]))
        self.assertLess(F.Range(1, 2), F.Range(F.Constant(3), F.Constant(4)))
        self.assertLess(F.Range(1, 2), F.Set([F.Constant(4), F.Constant(3)]))
        self.assertLess(F.Constant(F.Constant(F.Constant(1))), 2)
        self.assertEqual(
            min(F.Constant(F.Constant(F.Constant(1))), F.Constant(F.Constant(2))),
            F.Constant(F.Constant(F.Constant(1))),
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

            bcell = app.battery.specialize(F.ButtonCell())
            bcell.voltage.merge(3 * P.V)
            bcell.capacity.merge(F.Range.from_center(225 * P.mAh, 50 * P.mAh))
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
            self.assertIsInstance(r, F.Range, f"{type(r)}")

    def test_units(self):
        self.assertEqual(F.Constant(1e-9 * P.F), 1 * P.nF)


if __name__ == "__main__":
    unittest.main()

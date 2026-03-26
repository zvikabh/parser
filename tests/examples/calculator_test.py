import unittest

from parameterized import parameterized  # type: ignore[import-untyped]

from examples import calculator
import parser


class CalculatorTest(unittest.TestCase):

    @parameterized.expand([
        ['3+2', 5.0],
        ['-2+3', 1.0],
        ['3+5*2', 13.0],
        ['sqrt(9)+5**2', 28.0],
        ['3 + 5*(sqrt(5-1) * 4 / (2+2))', 13.0],
        ['abs(-2)', 2.0]
    ])
    def test_calculator(self, inp: str, expected: float) -> None:
        calc = calculator.Calculator()
        self.assertAlmostEqual(expected, calc.calc(inp))

    def test_invalid_function(self) -> None:
        calc = calculator.Calculator()
        with self.assertRaisesRegex(parser.ParserError, "Unknown function: FOOBAR"):
            calc.calc('foobar(5)')


if __name__ == '__main__':
    unittest.main()

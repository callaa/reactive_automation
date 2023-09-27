import unittest

from apps.reactive.reactive import parse_inputs, Expression, Entity


class TestInputExpressionParser(unittest.TestCase):
    def test_basic_operators(self):
        expr = parse_inputs("switch.a & sensor.b | switch.c")
        self.assertEqual(
            repr(expr),
            repr(
                Expression(
                    "&",
                    Entity("switch.a"),
                    Expression("|", Entity("sensor.b"), Entity("switch.c")),
                )
            ),
        )

    def test_whitespace(self):
        expr = parse_inputs(
            """switch.a&
            sensor.b

        |switch.c"""
        )

        self.assertEqual(
            repr(expr),
            repr(
                Expression(
                    "&",
                    Entity("switch.a"),
                    Expression("|", Entity("sensor.b"), Entity("switch.c")),
                )
            ),
        )

    def test_entity_values(self):
        expr = parse_inputs("switch.a=off & !cover=closed")
        self.assertEqual(
            repr(expr),
            repr(
                Expression(
                    "&",
                    Entity("switch.a", value="off"),
                    Entity("cover", invert=True, value="closed"),
                )
            ),
        )

    def test_parens(self):
        expr = parse_inputs(
            "switch.a & (sensor.b | switch.c & sensor.c) & (sensor.d | sensor.e)"
        )
        self.assertEqual(
            repr(expr),
            repr(
                Expression(
                    "&",
                    Entity("switch.a"),
                    Expression(
                        "&",
                        Expression(
                            "|",
                            Entity("sensor.b"),
                            Expression("&", Entity("switch.c"), Entity("sensor.c")),
                        ),
                        Expression("|", Entity("sensor.d"), Entity("sensor.e")),
                    ),
                )
            ),
        )

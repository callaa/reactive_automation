import unittest

from apps.reactive.reactive import parse_inputs, Expression, UnaryExpression, Entity
from operator import not_


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

    def test_negation(self):
        expr = parse_inputs("switch.a & !sensor.b")
        self.assertEqual(
            repr(expr),
            repr(
                Expression(
                    "&",
                    Entity("switch.a"),
                    UnaryExpression(not_, Entity("sensor.b")),
                )
            )
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
                    UnaryExpression(not_, Entity("cover", value="closed")),
                )
            ),
        )

    def test_parens(self):
        expr = parse_inputs(
            "switch.a & (sensor.b | switch.c & sensor.c) & (sensor.d | sensor.e) & !(sensor.f & sensor.g)"
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
                            Expression("&", Entity("switch.c"),
                                       Entity("sensor.c")),
                        ),
                        Expression(
                            '&',
                            Expression(
                                "|",
                                Entity("sensor.d"),
                                Entity("sensor.e")
                            ),
                            UnaryExpression(
                                not_,
                                Expression(
                                    '&',
                                    Entity('sensor.f'),
                                    Entity('sensor.g')
                                )
                            )
                        )
                    )
                )
            ),
        )

    def test_negated_parens(self):
        expr = parse_inputs(
            "!(sensor.b)"
        )
        self.assertEqual(
            repr(expr),
            repr(UnaryExpression(not_, Entity('sensor.b')))
        )

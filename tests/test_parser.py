import unittest

from apps.reactive.reactive import parse_inputs, Expression, UnaryExpression, Entity
from operator import not_, and_, or_


class TestInputExpressionParser(unittest.TestCase):
    def test_basic_operators(self):
        expr = parse_inputs("switch.a & sensor.b | switch.c")
        self.assertEqual(
            repr(expr),
            repr(
                Expression(
                    and_,
                    Entity("switch.a"),
                    Expression(or_, Entity("sensor.b"), Entity("switch.c")),
                )
            ),
        )

    def test_negation(self):
        expr = parse_inputs("switch.a & !sensor.b & sensor.c")
        self.assertEqual(
            repr(expr),
            repr(
                Expression(
                    and_,
                    Entity("switch.a"),
                    Expression(
                        and_,
                        UnaryExpression(not_, Entity("sensor.b")),
                        Entity("sensor.c"),
                    )
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
                    and_,
                    Entity("switch.a"),
                    Expression(or_, Entity("sensor.b"), Entity("switch.c")),
                )
            ),
        )

    def test_entity_values(self):
        expr = parse_inputs("switch.a=off & !cover=closed")
        self.assertEqual(
            repr(expr),
            repr(
                Expression(
                    and_,
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
                    and_,
                    Entity("switch.a"),
                    Expression(
                        and_,
                        Expression(
                            or_,
                            Entity("sensor.b"),
                            Expression(
                                and_,
                                Entity("switch.c"),
                                Entity("sensor.c")
                            ),
                        ),
                        Expression(
                            and_,
                            Expression(
                                or_,
                                Entity("sensor.d"),
                                Entity("sensor.e")
                            ),
                            UnaryExpression(
                                not_,
                                Expression(
                                    and_,
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
            "!(sensor.a & sensor.b) & sensor.c"
        )
        self.assertEqual(
            repr(expr),
            repr(
                Expression(
                    and_,
                    UnaryExpression(
                        not_,
                        Expression(
                            and_,
                            Entity("sensor.a"),
                            Entity("sensor.b")
                        )
                    ),
                    Entity("sensor.c"),
                )
            )
        )

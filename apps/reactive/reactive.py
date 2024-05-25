import hassapi
import operator
import datetime
import re


class ExpressionError(Exception):
    pass


BINARY_OPERATORS = ("&", "|")
UNARY_OPERATORS = ('!',)


class Expression:
    def __init__(self, op, left, right):
        if op == "&":
            self.operator = operator.and_
        elif op == "|":
            self.operator = operator.or_
        elif hasattr(op, '__call__'):
            self.operator = op
        else:
            raise ExpressionError(f"Unknown operator {op}")

        self.left = left
        self.right = right

    def __repr__(self):
        return f"({self.left} {self.operator.__name__} {self.right})"

    def entities(self):
        return self.left.entities() | self.right.entities()

    def evaluate(self, states):
        return self.operator(self.left.evaluate(states), self.right.evaluate(states))

    def replace_aliases(self, aliases):
        return Expression(
            self.operator,
            self.left.replace_aliases(aliases),
            self.right.replace_aliases(aliases)
        )


class UnaryExpression:
    def __init__(self, op, expr):
        self.operator = op
        self.expr = expr

    def __repr__(self):
        return f"{self.operator.__name__}({self.expr})"

    def entities(self):
        return self.expr.entities()

    def evaluate(self, states):
        return self.operator(self.expr.evaluate(states))

    def replace_aliases(self, aliases):
        return UnaryExpression(self.operator, self.expr.replace_aliases(aliases))


class Entity:
    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"{self.name}={self.value!r}" if self.value else self.name

    def entities(self):
        return set((self.name,))

    def evaluate(self, states):
        return states.get(self.name) == (self.value or 'on')

    def replace_aliases(self, aliases):
        try:
            alias = aliases[self.name]
        except KeyError:
            return self

        if self.value:
            if isinstance(alias, Entity):
                return Entity(alias.name, self.value)

            raise ExpressionError(
                "Value check can only be overridden for entity aliases")

        return alias


def parse_inputs(inputs, aliases=None):
    tokens = list(
        filter(lambda t: t != "", (t.strip()
               for t in re.split("([&|()!])", inputs)))
    )

    expr, remainder = parse_expression(tokens)
    if remainder:
        raise ExpressionError(f"Unparsed tokens: {remainder}")

    if aliases:
        expr = expr.replace_aliases(aliases)

    return expr


def parse_binary_expression(op, left, tokens):
    right, remainder = parse_expression(tokens)
    return Expression(op, left, right), remainder


def parse_parenthesized_expression(tokens):
    expr, remainder = parse_expression(tokens)
    if not remainder or remainder[0] != ")":
        raise ExpressionError("Expected ')'")

    return expr, remainder[1:]


def parse_unary_expression(op, tokens):
    assert (op == '!')  # the only unary op supported ATM

    next = tokens[0]

    if next == "(":
        operand, remainder = parse_parenthesized_expression(tokens[1:])

    elif next == ")":
        raise ExpressionError("Unexpected ')'")

    elif next in BINARY_OPERATORS or next in UNARY_OPERATORS:
        raise ExpressionError("Expected entity, not operator")

    else:
        operand = parse_entity(next)
        remainder = tokens[1:]

    return UnaryExpression(operator.not_, operand), remainder


def parse_entity(token):
    name = token
    value = None

    if "=" in name:
        name, value = name.split("=", 1)

    return Entity(name, value)


def parse_expression(tokens):
    if not tokens:
        raise ExpressionError("Expression truncated")

    next = tokens[0]

    if next == "(":
        entity, tokens = parse_parenthesized_expression(tokens[1:])

    elif next == ")":
        raise ExpressionError("Unexpected ')'")

    elif next in UNARY_OPERATORS:
        entity, tokens = parse_unary_expression(next, tokens[1:])

    elif next in BINARY_OPERATORS:
        raise ExpressionError("Expected entity, not operator")

    else:
        entity = parse_entity(next)
        tokens = tokens[1:]

    if tokens:
        if tokens[0] in BINARY_OPERATORS:
            entity, tokens = parse_binary_expression(
                tokens[0], entity, tokens[1:])

        elif tokens[0] != ")":
            raise ExpressionError(f"Expected operator, got {tokens}")

    return entity, tokens


class States:
    def __init__(self, app):
        self.cache = {}
        self.app = app

    def get(self, entity):
        if entity not in self.cache:
            self.cache[entity] = self.app.get_state(entity)

        return self.cache[entity]


class OutputRule:
    def __init__(self, output_entity, input_states, aliases={}):
        self.output_entity = output_entity
        self.input_states = [parse_inputs(i, aliases) for i in input_states]
        self.last_state = None

    def __repr__(self):
        return f"{self.output_entity} = {self.input_states}"

    def evaluate(self, states):
        new_state = any(i.evaluate(states) for i in self.input_states)

        if new_state is not self.last_state:
            self.last_state = new_state
            return new_state

        return None

    def update(self, hass):
        if self.last_state:
            hass.turn_on(self.output_entity)
        else:
            hass.turn_off(self.output_entity)


class Reactive(hassapi.Hass):
    def initialize(self):
        aliases = {
            name: parse_inputs(expr)
            for name, expr in self.args.get('aliases', {}).items()
        }

        rules = [
            OutputRule(out, inputs, aliases) for out, inputs in self.args["outputs"].items()
        ]

        # self.output_rules is an index that maps each output entity to its corresponding
        # set of rules. This is used when an output entity has been unavailable and
        # becomes available again to update its state.
        self.output_rules = {r.output_entity: r for r in rules}

        # self.rules is an index that maps each mentioned entity to the rules
        # it appears in. It is used to re-evaluate all relevant rules when
        # an entity changes state.
        self.rules = {}

        all_inputs = set()
        for rule in rules:
            inputs = set()
            for i in rule.input_states:
                inputs |= i.entities()

            all_inputs |= inputs
            for i in inputs:
                self.rules.setdefault(i, []).append(rule)

            self.log(f"{rule.output_entity} affected by {len(inputs)} input entities"
                     )

        self.log(f"Listening to {len(all_inputs)} inputs total.")
        self.listen_state(self.input_changed, list(all_inputs))

        # Trigger all the rules on startup and periodically to
        # ensure things haven't drifted out of sync
        self.trigger_all({"rules": rules})
        self.run_hourly(self.trigger_all, datetime.time(0, 0, 30), rules=rules)

        # Refresh state when output becomes available
        self.listen_state(
            self.output_becomes_available,
            [r.output_entity for r in rules],
            old="unavailable",
        )

    def trigger_all(self, cb_args):
        rules = cb_args["rules"]
        states = States(self)
        for rule in rules:
            rule.evaluate(states)
            rule.update(self)

    def input_changed(self, entity, attribute, old, new, kwargs):
        affected_rules = self.rules[entity]
        states = States(self)

        changes = 0
        for rule in affected_rules:
            change = rule.evaluate(states)
            if change is not None:
                rule.update(self)
                changes += 1

        if changes > 0:
            self.log(f"{entity} ({old} -> {new}): {len(affected_rules)} rules triggered, {changes} output states changed."
                     )

    def output_becomes_available(self, entity, attribute, old, new, kwargs):
        self.log(f"output {entity} became available again")
        self.output_rules[entity].update(self)

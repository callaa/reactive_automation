import hassapi
import operator
import datetime
import re


class ExpressionError(Exception):
    pass


OPERATORS = ("&", "|")


class Expression:
    def __init__(self, op, left, right):
        if op == "&":
            self.operator = operator.and_
        elif op == "|":
            self.operator = operator.or_
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


class Entity:
    def __init__(self, name, invert=False, value="on"):
        self.name = name
        self.invert = invert
        self.value = value

    def __repr__(self):
        if self.invert:
            return f"!{self.name}={self.value!r}"
        return f"{self.name}={self.value!r}"

    def entities(self):
        return set((self.name,))

    def evaluate(self, states):
        s = states.get(self.name) == self.value
        return s ^ self.invert


def parse_inputs(inputs):
    tokens = list(
        filter(lambda t: t != "", (t.strip() for t in re.split("([&|()])", inputs)))
    )

    expr, remainder = parse_expression(tokens)
    if remainder:
        raise ExpressionError(f"Unparsed tokens: {remainder}")

    return expr


def parse_binary_expression(op, left, tokens):
    right, remainder = parse_expression(tokens)
    return Expression(op, left, right), remainder


def parse_parenthesized_expression(tokens):
    expr, remainder = parse_expression(tokens)
    if not remainder or remainder[0] != ")":
        raise ExpressionError("Expected ')'")

    if len(remainder) > 1:
        next = remainder[1]
        if next in OPERATORS:
            return parse_binary_expression(next, expr, remainder[2:])
        else:
            raise ExpressionError(f"Expected operator, got {remainder[1:]}")

    return expr, []


def parse_entity(token):
    invert = False
    name = token
    value = "on"

    if token[0] == "!":
        invert = True
        name = token[1:]

    if "=" in name:
        name, value = name.split("=", 1)

    return Entity(name, invert, value)


def parse_expression(tokens):
    if not tokens:
        raise ExpressionError("Expression truncated")

    next = tokens[0]

    if next == "(":
        return parse_parenthesized_expression(tokens[1:])

    elif next == ")":
        raise ExpressionError("Unexpected ')'")

    elif next in OPERATORS:
        raise ExpressionError("Expected entity, not operator")

    entity = parse_entity(next)
    tokens = tokens[1:]
    if tokens:
        if tokens[0] in OPERATORS:
            return parse_binary_expression(tokens[0], entity, tokens[1:])
        elif tokens[0] == ")":
            return entity, tokens
        else:
            raise ExpressionError(f"Expected operator, got {tokens}")

    else:
        return entity, []


class States:
    def __init__(self, app):
        self.cache = {}
        self.app = app

    def get(self, entity):
        if entity not in self.cache:
            self.cache[entity] = self.app.get_state(entity)

        return self.cache[entity]


class OutputRule:
    def __init__(self, output_entity, input_states):
        self.output_entity = output_entity
        self.input_states = [parse_inputs(i) for i in input_states]
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
        rules = [
            OutputRule(out, inputs) for out, inputs in self.args["outputs"].items()
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

            self.log(f"{rule.output_entity} affected by {len(inputs)} input entities")

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
            self.log(
                f"{entity} ({old} -> {new}): {len(affected_rules)} rules triggered, {changes} output states changed."
            )

    def output_becomes_available(self, entity, attribute, old, new, kwargs):
        self.log(f"output {entity} became available again")
        self.output_rules[entity].update(self)

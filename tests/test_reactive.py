import unittest

from apps.reactive.reactive import Reactive


class TestReactiveApp(unittest.TestCase):
    def test_ands(self):
        app = Reactive(
            {
                "outputs": {
                    "light.test": [
                        "binary_sensor.motion & binary_sensor.dark",
                        "binary_sensor.lightswitch",
                    ]
                }
            }
        )

        self.assertEqual(app.mock_states, {"light.test": "off"})

        app.log("### Turning on the light switch turns the light on")
        app.turn_on("binary_sensor.lightswitch")
        self.assertEqual(
            app.mock_states, {
                "binary_sensor.lightswitch": "on", "light.test": "on"}
        )

        app.log("### Light switch off")
        app.turn_off("binary_sensor.lightswitch")
        self.assertEqual(
            app.mock_states, {
                "binary_sensor.lightswitch": "off", "light.test": "off"}
        )

        app.log("### Motion detected (but not dark yet)")
        app.turn_on("binary_sensor.motion")
        self.assertEqual(
            app.mock_states,
            {
                "binary_sensor.lightswitch": "off",
                "binary_sensor.motion": "on",
                "light.test": "off",
            },
        )

        app.log("### Motion detected (and now it's dark too)")
        app.turn_on("binary_sensor.dark")
        self.assertEqual(
            app.mock_states,
            {
                "binary_sensor.lightswitch": "off",
                "binary_sensor.motion": "on",
                "binary_sensor.dark": "on",
                "light.test": "on",
            },
        )

    def test_output_change(self):
        app = Reactive(
            {"outputs": {"light.test": ["binary_sensor.lightswitch"]}})

        self.assertEqual(app.mock_states, {"light.test": "off"})

        app.log(
            "### If the output is switched on outside the script, it should stay on"
        )
        app.turn_on("light.test")
        self.assertEqual(app.mock_states, {"light.test": "on"})

        app.log(
            "### The output's state is remembered so we don't issue extra turn ons/offs"
        )
        app.turn_off("binary_sensor.lightswitch")
        self.assertEqual(
            app.mock_states, {
                "binary_sensor.lightswitch": "off", "light.test": "on"}
        )

        app.log(
            "### Periodically though, we force a sync of the input to output states"
        )
        app.mock_run_hourly()
        self.assertEqual(
            app.mock_states, {
                "binary_sensor.lightswitch": "off", "light.test": "off"}
        )

    def test_output_becomes_available(self):
        app = Reactive(
            {"outputs": {"light.test": ["binary_sensor.lightswitch"]}})

        # Switch is turned on but the smart light is unavailable (unplugged)
        app.mock_set_state("binary_sensor.lightswitch", "on")
        app.mock_set_state("light.test", "unavailable")

        self.assertEqual(
            app.mock_states,
            {
                "binary_sensor.lightswitch": "on",
                "light.test": "unavailable",
            },
        )

        app.log("### Smart light is powered on. State should be synced now")
        app.mock_set_state("light.test", "off")
        self.assertEqual(
            app.mock_states, {
                "binary_sensor.lightswitch": "on", "light.test": "on"}
        )

    def test_parenthesis(self):
        app = Reactive(
            {
                "outputs": {
                    "light.test": [
                        "binary_sensor.motion & (dark | cover=closed)",
                    ]
                }
            }
        )

        self.assertEqual(app.mock_states, {"light.test": "off"})

        app.log("### Motion detected (but not dark yet and curtains not closed)")
        app.turn_on("binary_sensor.motion")
        self.assertEqual(
            app.mock_states, {
                "binary_sensor.motion": "on", "light.test": "off"}
        )

        app.log("### Motion detected and it's dark")
        app.turn_on("dark")
        self.assertEqual(
            app.mock_states,
            {"binary_sensor.motion": "on", "dark": "on", "light.test": "on"},
        )

        app.log("### Motion detected and curtains closed (and still dark)")
        app.mock_set_state("cover", "closed")
        self.assertEqual(
            app.mock_states,
            {
                "binary_sensor.motion": "on",
                "dark": "on",
                "cover": "closed",
                "light.test": "on",
            },
        )

        app.log("### Motion detected and curtains closed (no longer dark)")
        app.turn_off("dark")
        self.assertEqual(
            app.mock_states,
            {
                "binary_sensor.motion": "on",
                "dark": "off",
                "cover": "closed",
                "light.test": "on",
            },
        )

        app.log("### Motion detected and curtains opened")
        app.mock_set_state("cover", "open")
        self.assertEqual(
            app.mock_states,
            {
                "binary_sensor.motion": "on",
                "dark": "off",
                "cover": "open",
                "light.test": "off",
            },
        )

    def test_negations(self):
        app = Reactive(
            {
                "outputs": {
                    "light.test": [
                        "binary_sensor.motion & !binary_sensor.light",
                    ]
                }
            }
        )

        self.assertEqual(
            app.mock_states,
            {
                "light.test": "off",
            },
        )

        app.log("### Motion detected and it's not light out")
        app.turn_on("binary_sensor.motion")
        self.assertEqual(
            app.mock_states,
            {
                "binary_sensor.motion": "on",
                "light.test": "on",
            },
        )

        app.log("### Motion detected and it *is* light out")
        app.turn_on("binary_sensor.light")
        self.assertEqual(
            app.mock_states,
            {
                "binary_sensor.motion": "on",
                "binary_sensor.light": "on",
                "light.test": "off",
            },
        )

    def test_multiple_outputs(self):
        app = Reactive(
            {
                "outputs": {
                    "light.test1": ["sensor0", "sensor1"],
                    "light.test2": ["sensor0", "sensor2"],
                }
            }
        )

        self.assertEqual(
            app.mock_states,
            {
                "light.test1": "off",
                "light.test2": "off",
            },
        )

        app.turn_on("sensor0")
        self.assertEqual(
            app.mock_states,
            {
                "sensor0": "on",
                "light.test1": "on",
                "light.test2": "on",
            },
        )

        app.turn_off("sensor0")
        self.assertEqual(
            app.mock_states,
            {
                "sensor0": "off",
                "light.test1": "off",
                "light.test2": "off",
            },
        )

        app.turn_on("sensor1")
        self.assertEqual(
            app.mock_states,
            {
                "sensor0": "off",
                "sensor1": "on",
                "light.test1": "on",
                "light.test2": "off",
            },
        )

        app.turn_off("sensor1")
        app.turn_on("sensor2")
        self.assertEqual(
            app.mock_states,
            {
                "sensor0": "off",
                "sensor1": "off",
                "sensor2": "on",
                "light.test1": "off",
                "light.test2": "on",
            },
        )

    def test_aliases(self):
        app = Reactive(
            {
                "aliases": {
                    "switch": "binary_sensor.switch_with_long_id",
                    "is_dark": "binary_sensor.dark | input_boolean.bedtime"
                },
                "outputs": {
                    "light.test": [
                        "binary_sensor.motion & is_dark",
                        "switch",
                    ]
                }
            }
        )

        self.assertEqual(app.mock_states, {"light.test": "off"})

        app.log("### Turning on the light switch turns the light on")
        app.turn_on("binary_sensor.switch_with_long_id")
        self.assertEqual(
            app.mock_states, {
                "binary_sensor.switch_with_long_id": "on", "light.test": "on"}
        )

        app.log("### Light switch off")
        app.turn_off("binary_sensor.switch_with_long_id")
        self.assertEqual(
            app.mock_states, {
                "binary_sensor.switch_with_long_id": "off", "light.test": "off"}
        )

        app.log("### Motion detected (but not dark yet)")
        app.turn_on("binary_sensor.motion")
        self.assertEqual(
            app.mock_states,
            {
                "binary_sensor.switch_with_long_id": "off",
                "binary_sensor.motion": "on",
                "light.test": "off",
            },
        )

        app.log("### Motion detected (and it's bedtime)")
        app.turn_on("input_boolean.bedtime")
        self.assertEqual(
            app.mock_states,
            {
                "binary_sensor.switch_with_long_id": "off",
                "binary_sensor.motion": "on",
                "input_boolean.bedtime": "on",
                "light.test": "on",
            },
        )

    def test_alias_entity_negation(self):
        app = Reactive(
            {
                "aliases": {
                    "entity": "binary_sensor.switch",
                },
                "outputs": {
                    "light.test": [
                        "!entity",
                    ]
                }
            }
        )

        self.assertEqual(app.mock_states, {"light.test": "on"})

        app.turn_on("binary_sensor.switch")
        self.assertEqual(
            app.mock_states, {
                "binary_sensor.switch": "on", "light.test": "off"}
        )

    def test_alias_expression_negation(self):
        app = Reactive(
            {
                "aliases": {
                    "expr": "binary_sensor.switch | binary_sensor.dark",
                },
                "outputs": {
                    "light.test": [
                        "!expr",
                    ]
                }
            }
        )

        self.assertEqual(app.mock_states, {"light.test": "on"})

        app.turn_on("binary_sensor.switch")
        self.assertEqual(
            app.mock_states, {
                "binary_sensor.switch": "on", "light.test": "off"}
        )

# Mock hassapi for unit testing

PRINT = False


class Hass:
    def __init__(self, args):
        self.mock_states = {}
        self.mock_listeners = {}
        self.mock_run_hourly = None

        self.args = args
        self.initialize()

    def log(self, msg):
        if PRINT:
            print("LOG:", msg)

    def run_hourly(self, callback, *args, **kwargs):
        self.mock_run_hourly = lambda: callback(kwargs)

    def listen_state(self, callback, states, old=None):
        for s in states:
            self.mock_listeners.setdefault(s, []).append((callback, old))

    def get_state(self, entity):
        return self.mock_states.get(entity)

    def turn_on(self, entity):
        self.mock_set_state(entity, "on")

    def turn_off(self, entity):
        self.mock_set_state(entity, "off")

    def mock_set_state(self, entity, new_state):
        old = self.mock_states.get(entity)
        self.mock_states[entity] = new_state

        for listener, old_state in self.mock_listeners.get(entity, ()):
            if old_state is None or old_state == old:
                # note: attribute argument is unused in our coude
                # note: kwargs argument is unused in our code
                listener(entity, None, old, new_state, None)

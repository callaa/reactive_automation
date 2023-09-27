Reactive Automations for Home Assistant
----------------------------------------

This is an AppDaemon script for Home Assistant that lets you easily define automations that sets the state of an output entity based on the states of one or more input entities.

For example, say you have a light (`light.stairs`) that should turn on when either of two motions sensors (`binary_sensor.porch_occupancy` and `binary_sensor.stairs_occupancy`) pick up motion, but only when it's dark (`binary_sensor.dark_outside`), or when the curtains are closed (`cover.porch`), but not when a "night mode" flag (`switch.nightmode`) is set. You also have a light switch (`binary_sensor.stairs_lightswitch`) that should turn on the light always. While you can do this with Home Assistant's automations (or Node Red) alone, it's a bit laborious and error prone, especially if you have to do it for many lights!

With reactive.py, creating these rules is as simple as putting this into your `apps.yaml` file:

  reactive:
    module: reactive
    class: Reactive
    outputs:
      light.stairs:
        - (binary_sensor.porch_occupancy | binary_sensor.stairs_occupancy) & (binary_sensor.dark_outside | cover.porch=closed) & binary_sensor.dark_outside & !switch.nightmode
        - binary_sensor.stairs_lightswitch


Reactive.py monitors all the named input entities for changes and turns the output either on or off when the rule evalutes to a new state.
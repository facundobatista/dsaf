# Copyright 2023-2024 Facundo Batista
# https://github.com/facundobatista/dsaf

"""The Framework FSM."""

import gc
import uasyncio

from src import logger
from src.networkmanager import NetworkManager, NetworkError


def load_config(filepath):
    """Load a config from file.

    Very simple structure: key/values separated by colon, single line.
    """
    with open(filepath, "rt") as fh:
        lines = [x.strip() for x in fh]
    keyvals = [line.split(":", 1) for line in lines if line]
    return {k: v.strip() for k, v in keyvals}


class FrameworkFSM:
    # states
    ST_STARTED = "started"
    ST_STEADY = "steady state"
    ST_ERROR_NO_CONFIG = "error no config"
    ST_LOADING_CONFIG = "loading config"
    # ST_BAD_CONFIG = "error cannot load config"      still unclear about this one
    ST_ERROR_NO_SERVER = "error no server"
    ST_ERROR_UNKNOWN = "error unknown"
    ST_LOW_BATTERY = "error battery low"

    # events
    EV_INIT_OK = "init ok"
    EV_MISSING_CONFIG = "missing config"
    EV_CONFIGURATOR_DETECTED = "configurator detected"
    EV_CONFIG_LOADED = "configuration loaded"
    EV_ERROR_NO_SERVER = "no server comm"
    EV_LOW_BATTERY = "battery low"
    EV_EXCEPTION = "unexpected exception"
    EV_SERVER_OK = "server ok"

    # transitions: from-state + event -> new-state + function-to-call
    _transitions = {
        # bootstrap
        (None, None): (ST_STARTED, "init"),  # bootstrap
        # generic error triggered by an exception
        (None, EV_EXCEPTION): (ST_ERROR_UNKNOWN, "handle_unknown_error"),
        # regular transitions
        (ST_STARTED, EV_INIT_OK): (ST_STEADY, "steady_operation"),
        (ST_STARTED, EV_MISSING_CONFIG): (ST_ERROR_NO_CONFIG, "no_config"),
        (ST_ERROR_NO_CONFIG, EV_CONFIGURATOR_DETECTED): (ST_LOADING_CONFIG, "load_config"),
        (ST_LOADING_CONFIG, EV_CONFIG_LOADED): (ST_STEADY, "steady_operation"),
        (ST_STEADY, EV_ERROR_NO_SERVER): (ST_ERROR_NO_SERVER, "handle_server_error"),
        (ST_STEADY, EV_LOW_BATTERY): (ST_LOW_BATTERY, "steady_operation"),
        (ST_ERROR_NO_SERVER, EV_SERVER_OK): (ST_STEADY, "steady_operation"),
    }

    # status leds for the different states (green, blue); each item has two values
    # - the first is if it blinks
    # - the second depends on if it blinks
    #     - if no, if it's on or off
    #     - if yes the on/off sequence
    _leds_status = {
        # Full on | Off
        ST_STARTED: (
            (False, True),
            (False, False),
        ),
        # Short blink every 5 seconds | Off
        ST_STEADY: (
            (True, [200, 4800]),
            (False, False),
        ),
        # 1.5 s ~square waveform blink | Short 1 time blink every 3 seconds
        ST_ERROR_NO_CONFIG: (
            (True, [1400, 1600]),
            (True, [200, 2800]),
        ),
        # 200 ms square waveform blink | Off | Configurator detected; actively working with it |
        ST_LOADING_CONFIG: (
            (True, [200, 200]),
            (False, False),
        ),
        # 1.5 s ~square waveform blink | Short 2 times blinks every 3 seconds
        ST_ERROR_NO_SERVER: (
            (True, [1400, 1600]),
            (True, [200, 400, 200, 2200]),
        ),
        # 1.5 s ~square waveform blink | Full on
        ST_ERROR_UNKNOWN: (
            (True, [1400, 1600]),
            (False, True),
        ),
        # 2 s square waveform blink | 2 s square waveform blink
        ST_LOW_BATTERY: (
            (True, [2000, 2000]),
            (True, [2000, 2000]),
        ),
    }

    def __init__(self, sensor_class, status_led_green, status_led_red):
        self.status_led_green = status_led_green
        self.status_led_red = status_led_red
        self.config = load_config("system.cfg")

        host, port = self.config['manager-host'], self.config['manager-port']
        self.status_url = f"http://{host}:{port}/v1/status/"

        self.current_state = None
        self.sensor_manager = None
        self.network_manager = NetworkManager(
            self.config["wifi-ssid"], self.config["wifi-password"])
        self.sensor_class = sensor_class

    def _set_led(self, led, status):
        """Set a led to a specific status."""
        shall_blink, light_info = status
        if shall_blink:
            led.blink(light_info)
        else:
            led.set(light_info)

    def _set_leds(self):
        """Set the leds according to current state."""
        logger.debug("Set led for state {}", self.current_state)
        green_info, red_info = self._leds_status[self.current_state]
        self._set_led(self.status_led_green, green_info)
        self._set_led(self.status_led_red, red_info)

    def _transition(self, transition_event):
        """Transition from one state to the other and set leds properly."""
        logger.info(
            "Framework transition from state {!r} by event {!r}",
            self.current_state, transition_event)
        self.current_state, function_name = self._transitions[
            (self.current_state, transition_event)]
        logger.info("Framework new state: {!r}", self.current_state)
        function = getattr(self, function_name)
        self._set_leds()
        return function

    async def loop(self):
        """Wrap the main loop around a try/except for robust information set."""
        function = self._transition(None)
        while True:
            try:
                event = await function()
            except Exception as exc:
                # XXX log this to disk?
                print("================ UNKN Exc", exc)
                self.current_state = None
                function = self._transition(self.EV_EXCEPTION)
                function(exc)
                print("============ exit????")
                break
            else:
                function = self._transition(event)

    async def init(self):
        """Initiate the process."""
        self.sensor_manager = self.sensor_class(self.config)

        # set up status sending to the server every 10s
        uasyncio.create_task(self._send_status())

        return self.EV_INIT_OK

    async def _send_status(self):
        """Send status information to the server."""
        while True:
            gc.collect()
            free_mem = gc.mem_free()
            # prepare the status
            payload = {
                "foo": 3,
                "free-memory": free_mem,
            }  # XXX: better info! ping time to server and current datetime

            # send it to the manager
            try:
                await self.network_manager.hit(self.status_url, payload)
            except NetworkError:
                pass
            await uasyncio.sleep_ms(10000)

    async def steady_operation(self):
        """Main working ok state."""
        host, port = self.config['manager-host'], self.config['manager-port']
        url = f"http://{host}:{port}/v1/report/"

        while True:
            logger.debug("Steady operation, reporting to {}", url)

            data = self.sensor_manager.get()
            try:
                response = await self.network_manager.hit(url, data)
            except NetworkError:
                return self.EV_ERROR_NO_SERVER

            logger.debug("Server response: {}", response)
            await uasyncio.sleep_ms(5000)

            # XXX: handle battery being low

    def load_config(self):
        """Deal with the configurator node."""
        # XXX: to be implemented

    def no_config(self):
        """No config, wait for configurator."""
        # XXX: to be implemented

    def handle_server_error(self):
        """Handle a miscomunication to the server."""
        counter = 0
        while True:
            await uasyncio.sleep_ms(2000)
            payload = {
                "checking-server": counter,
            }
            try:
                logger.debug("Server error check attempt {}", counter)
                await self.network_manager.hit(self.status_url, payload)
            except NetworkError:
                pass
            else:
                return self.EV_SERVER_OK

    def handle_unknown_error(self, exc):
        """Handle a generic unknown error."""
        # XXX: to be implemented
        logger.info("Unkwnown error: {!r}", exc)

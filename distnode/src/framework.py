# Copyright 2023-2024 Facundo Batista
# https://github.com/facundobatista/dsaf

"""The Framework FSM."""

import gc

from src import logger, multitimer


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

    # transitions: from-state + event -> new-state + function-to-call
    _transitions = {
        # bootstrap
        (None, None): (ST_STARTED, "init"),  # bootsrap
        # generic error triggered by an exception
        (None, EV_EXCEPTION): (ST_ERROR_UNKNOWN, "handle_unknown_error"),
        # regular transitions
        (ST_STARTED, EV_INIT_OK): (ST_STEADY, "steady_operation"),
        (ST_STARTED, EV_MISSING_CONFIG): (ST_ERROR_NO_CONFIG, "no_config"),
        (ST_ERROR_NO_CONFIG, EV_CONFIGURATOR_DETECTED): (ST_LOADING_CONFIG, "load_config"),
        (ST_LOADING_CONFIG, EV_CONFIG_LOADED): (ST_STEADY, "steady_operation"),
        (ST_STEADY, EV_ERROR_NO_SERVER): (ST_ERROR_NO_SERVER, "handle_server_error"),
        (ST_STEADY, EV_LOW_BATTERY): (ST_LOW_BATTERY, "steady_operation"),
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

    def __init__(self, network_manager, sensor_class, status_led_green):
        self.status_led_green = status_led_green
        # XXX: incorporate blue led

        # XXX: this should be loaded from disk or set by the configurator!!
        self.config = {
            "manager-host": "192.168.100.5",
            "manager-port": 5000,
            "wifi-ssid": "Illapa",
            "wifi-password": "Orko1249",
        }
        self.current_state = None
        self.sensor_manager = None
        self.network_manager = network_manager
        self.sensor_class = sensor_class

        # set up status sending to the server every 10s
        host, port = self.config['manager-host'], self.config['manager-port']
        self.status_url = f"http://{host}:{port}/v1/status/"
        timer = multitimer.Timer("status")
        timer.init(period=10000, mode=multitimer.PERIODIC, callback=self._send_status)

    def _send_status(self, _):
        """Send status information to the server."""
        gc.collect()
        free_mem = gc.mem_free()
        print("Free memory:", free_mem)
        # prepare the status
        payload = {
            "foo": 3,
            "free-memory": free_mem,
        }  # XXX: better info! ping time to server and current datetime

        # send it to the manager
        self.network_manager.hit(self.status_url, payload)

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
        green_info, blue_info = self._leds_status[self.current_state]
        self._set_led(self.status_led_green, green_info)
        # XXX: handle blue led

    def _transition(self, transition_event):
        """Transition from one state to the other and set leds properly."""
        logger.info(
            "Framework transition from state{!r} by event {!r}",
            self.current_state, transition_event)
        self.current_state, function_name = self._transitions[
            (self.current_state, transition_event)]
        logger.info("Framework new state: {!r}", self.current_state)
        function = getattr(self, function_name)
        self._set_leds()
        return function

    def _loop(self):
        """Real main loop."""
        function = self._transition(None)

        while True:
            event = function()
            function = self._transition(event)

    def loop(self):
        """Wrap the main loop around a try/except for robust information set."""
        try:
            self._loop()
        except Exception as exc:
            # XXX log this to disk?
            self.current_state = None
            function = self._transition(self.EV_EXCEPTION)
            function(exc)

    def init(self):
        """Initiate the process."""
        # XXX: handle missing config (or not)

        self.sensor_manager = self.sensor_class(self.config)

        # connect to the network
        self.network_manager.connect(self.config["wifi-ssid"], self.config["wifi-password"])

        # # going into normal mode
        # status_led.blink(4500, 500)

        # XXX cannot have the same timer to do two things, we'll need to implement a
        # virtual timer/scheduler or something
        # timer.init(period=send_status, mode=machine.Timer.PERIODIC, callback=send_status)

        return self.EV_INIT_OK

    def _steady(self, timer):
        """Do all processing in stady state."""
        print("======== steady!", timer)
        host, port = self.config['manager-host'], self.config['manager-port']
        url = f"http://{host}:{port}/v1/report/"
        logger.debug("Steady operation, reporting to {}", url)

        data = self.sensor_manager.get()
        try:
            response = self.network_manager.hit(url, data)
        #except NetworkManagerError:
        except Exception as err:
            print("======= pumba!", repr(err))
            # XXX: transition to other state here!!!
            timer.deinit()
            return

        logger.debug("Server response: {}", response)

        # XXX: handle battery being low

==== tick! 1
       3.439  NetworkManager: connected!
       3.450  Framework transition from state'started' by event 'init ok'
       3.467  Framework new state: 'steady state'
       3.480  Set led for state steady state
       3.497  Framework transition from state'steady state' by event None
       3.511  Framework transition from stateNone by event 'unexpected exception'
       3.525  Framework new state: 'error unknown'
       3.538  Set led for state error unknown
       3.554  Unkwnown error: KeyError(('steady state', None),)

    def steady_operation(self):
        """Main working ok state."""
        timer = multitimer.Timer("steady")
        timer.init(period=2000, mode=multitimer.PERIODIC, callback=self._steady)

    def load_config(self):
        """Deal with the configurator node."""
        # XXX: to be implemented

    def no_config(self):
        """No config, wait for configurator."""
        # XXX: to be implemented

    def handle_server_error(self):
        """Handle a miscomunication to the server."""
        # XXX: to be implemented
        #  - sleep a couple of seconds
        #  - try if server is fine (hit it with a HEAD or something)
        #  - if yes, return transition to steady state
        #  - if not (NetworkManagerError), GOTO 10

    def handle_unknown_error(self, exc):
        """Handle a generic unknown error."""
        # XXX: to be implemented
        logger.info("Unkwnown error: {!r}", exc)

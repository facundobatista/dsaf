# Copyright 2023-2024 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Distributed node framework."""

import json
import time
from urllib import urequest

import machine
import micropython
import network

from src import logger
from src import multitimer
from src.framework import FrameworkFSM
from src.sensor import ExampleSensorManager

# recommended for systems that handles ISR
micropython.alloc_emergency_exception_buf(100)


class Led:
    """Manage a led."""

    def __init__(self, pin_id):
        self.led = machine.Pin(pin_id, machine.Pin.OUT)  # "active low"; IOW "inversed"
        self.blink_idx = None
        self.blink_on = None
        self.timer = multitimer.Timer(f"led pin={pin_id}")

    def set(self, on):
        """Turn on (on=True) or off (on=False) the led permanently."""
        # note the led is inversed!!
        if on:
            self.led.off()
        else:
            self.led.on()

    def blink(self, delays_sequence):
        """Blink the led, passing some time on, then some time off, loop.

        Accepts any sequence of delays, starting with "time in on", with two restrictions:
        - time in milliseconds
        - the sequence must be of even quantity of values
        """
        if len(delays_sequence) % 2:
            raise ValueError("The sequence must be of even quantity of values")

        # cancel any previous blinking
        self.timer.deinit()

        self.blink_on = False  # starts with ligth on (inversed!)
        self.blink_idx = 0

        def _step(_):
            if self.blink_on:
                self.led.on()
            else:
                self.led.off()
            self.blink_on = not self.blink_on

            delay = delays_sequence[self.blink_idx]
            self.blink_idx += 1
            if self.blink_idx == len(delays_sequence):
                self.blink_idx = 0

            self.timer.init(period=delay, mode=multitimer.ONE_SHOT, callback=_step)

        _step(None)


class NetworkManager:
    def __init__(self):
        self.ssid = None
        self.password = None
        self.wlan = None

    def connect(self, ssid, password):
        """Connect to the network."""
        logger.info("NetworkManager: connect")
        self.ssid = ssid
        self.password = password

        if self.wlan is not None and self.wlan.isconnected():
            logger.debug("NetworkManager: already connected, disconnecting...")
            self.wlan.disconnect()

        self.wlan = network.WLAN(network.STA_IF)  # create station interface
        self.wlan.active(True)  # activate the interface
        self.wlan.connect(self.ssid, self.password)
        while not self.wlan.isconnected():
            logger.debug("NetworkManager: waiting for connection...")
            time.sleep(1)
        logger.info("NetworkManager: connected!", self.wlan.ifconfig())

    def hit(self, url, payload):
        """Do a POST to an url with a json-able payload."""
        logger.debug("Network hit {} with {}", url, payload)
        data = json.dumps(payload).encode("ascii")
        try:
            resp = urequest.urlopen(url, data=data)
        except OSError as exc:
            if exc.errno == 103:
                logger.debug("Network connection lost")
                # connection broken, reconnect and retry
                self.connect(self.ssid, self.password)
                resp = urequest.urlopen(url, data=data)
            else:
                print("=========== unknown OSError", exc.errno)
                raise
            # XXX: also support server down
            #       OSError(104,)
            #       raise NetworkManagerError specific thing
        content = resp.read()
        resp.close()
        return content


machine_timer = machine.Timer(-1)


def timer_hook(_):
    """Main timer hook, called by hardware.

    This one MUST do almost nothing, but just schedule the multitimer tick.
    """
    micropython.schedule(multitimer.tick, None)


def run():
    """Set up everything and run."""
    logger.info("Start")
    # XXX: use an external led for this!
    green_led = Led(2)

    # hook the machine timer
    machine_timer.init(
        period=multitimer.TICK_DELAY,
        mode=machine.Timer.PERIODIC,
        callback=timer_hook)

    fsm = FrameworkFSM(NetworkManager(), ExampleSensorManager, green_led)
    fsm.loop()

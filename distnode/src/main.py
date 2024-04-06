# Copyright 2023-2024 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Distributed node framework."""

import json
import uasyncio
from urllib import urequest

import machine
import micropython
import network

from src import logger
from src.framework import FrameworkFSM
from src.sensor import ExampleSensorManager

# recommended for systems that handles ISR
micropython.alloc_emergency_exception_buf(100)


class Led:
    """Manage a led."""

    def __init__(self, pin_id, inverted=False):
        self.inverted = inverted
        self.led = machine.Pin(pin_id, machine.Pin.OUT)  # "active low"
        self.blink_task = None

    def set(self, on):
        """Turn on (on=True) or off (on=False) the led permanently."""
        if self.blink_task is not None:
            self.blink_task.cancel()
            self.blink_task = None

        if self.inverted:
            on = not on
        if on:
            self.led.on()
        else:
            self.led.off()

    async def _blink(self, delays_sequence):
        """Really blink."""
        blink_on = not self.inverted  # starts with ligth on
        blink_idx = 0

        while True:
            if blink_on:
                self.led.on()
            else:
                self.led.off()
            blink_on = not blink_on

            delay = delays_sequence[blink_idx]
            blink_idx += 1
            if blink_idx == len(delays_sequence):
                blink_idx = 0

            await uasyncio.sleep_ms(delay)

    def blink(self, delays_sequence):
        """Blink the led, passing some time on, then some time off, loop.

        Accepts any sequence of delays, starting with "time in on", with two restrictions:
        - time in milliseconds
        - the sequence must be of even quantity of values
        """
        if len(delays_sequence) % 2:
            raise ValueError("The sequence must be of even quantity of values")

        # cancel any previous blinking
        if self.blink_task is not None:
            self.blink_task.cancel()

        self.blink_task = uasyncio.create_task(self._blink(delays_sequence))


class NetworkManager:
    def __init__(self):
        self.ssid = None
        self.password = None
        self.wlan = None

    async def connect(self, ssid, password):
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
            await uasyncio.sleep_ms(1000)
        logger.info("NetworkManager: connected!", self.wlan.ifconfig())

    async def hit(self, url, payload):
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


async def run():
    """Set up everything and run."""
    logger.info("Start")
    internal_led = Led(2, inverted=True)  # internal
    internal_led.set(True)

    green_led = Led(4)
    red_led = Led(5)

    fsm = FrameworkFSM(NetworkManager(), ExampleSensorManager, green_led, red_led)
    await fsm.loop()

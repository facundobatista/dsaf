# Copyright 2023-2024 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Distributed node framework."""

import uasyncio

import machine
import micropython

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


async def run():
    """Set up everything and run."""
    logger.info("Start")
    internal_led = Led(2, inverted=True)  # internal
    internal_led.set(True)

    green_led = Led(4)
    red_led = Led(5)

    fsm = FrameworkFSM(ExampleSensorManager, green_led, red_led)
    await fsm.loop()

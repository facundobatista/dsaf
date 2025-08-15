# Copyright 2025 Facundo Batista
# https://github.com/facundobatista/dsaf/

"""Led management."""

import asyncio

import machine


class Led:
    """Manage a led."""

    def __init__(self, pin_id, inverted=False):
        self.inverted = inverted
        self.led = machine.Pin(pin_id, machine.Pin.OUT)  # "active low"
        self.blink_task = None

    def set(self, state):
        """Turn on (state=True) or off (state=False) the led permanently."""
        if self.blink_task is not None:
            # no blinking if set to a fixed state
            self.blink_task.cancel()
            self.blink_task = None

        if self.inverted:
            state = not state
        if state:
            self.led.on()
        else:
            self.led.off()

    async def _blink(self, delays_sequence, once):
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

                if once:
                    # sequence is finished, time to go
                    return

            await asyncio.sleep_ms(delay)

    def start_blinking(self, delays_sequence):
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

        self.blink_task = asyncio.create_task(self._blink(delays_sequence, False))

    async def blink_once(self, delays_sequence):
        """Blink the led, following the received sequence just once.

        Accepts any sequence of delays, starting with "time in on"; the time is
        in milliseconds
        """
        await self._blink(delays_sequence, True)

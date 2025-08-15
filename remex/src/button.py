# Copyright 2025 Facundo Batista
# https://github.com/facundobatista/dsaf/

import asyncio

import machine

from src import logger


class Button:
    """Manage a button."""

    IRQ_POLLING = 20  # how many ms between checks
    IRQ_MINIMUM_SEQ = 10  # minimum of consecutive checks in positive to trigger the interrupt

    def __init__(self, pin_id, name=None):
        self.name = name if name else pin_id
        self.pin = machine.Pin(pin_id, machine.Pin.IN, machine.Pin.PULL_UP)
        self.current_task = None

    @property
    def pressed(self):
        """Return if the button is pressed.

        Note that as it has a pull up resistor (see __init__) when the button is pressed
        it contacts the pin to ground, so for "button pressed mean 1" we need to invert here.
        """
        return not self.pin.value()

    def set_interrupt(self, delay_ms, callback, *args, **kwargs):
        """Set a function to be called when the button is left pressed.

        The button needs to be hold pressed for at least 'delay_ms' milliseconds to trigger
        the callback. A typical value is 200 ms for a "simple button press" (not really
        "holding" it).
        """
        if delay_ms % self.IRQ_POLLING:
            delay_ms = (delay_ms // self.IRQ_POLLING) * self.IRQ_POLLING
            logger.error(
                "Callback delay should be multiple of IRQ_POLLING, fixing to {}", delay_ms)
        if delay_ms < self.IRQ_POLLING * self.IRQ_MINIMUM_SEQ:
            delay_ms = self.IRQ_POLLING * self.IRQ_MINIMUM_SEQ
            logger.error("Callback delay too small, fixing to {}", delay_ms)
        sequence_trigger = delay_ms // self.IRQ_POLLING

        if self.current_task is not None and self.current_task is not asyncio.current_task():
            # if present, cancel current task (it is ok to cancel if already finished, it's a
            # no-op); also avoid cancelling if it's the *current* task (the called callback may
            # be setting a new interrupt, but that's fine, it's in the process of finishing
            self.current_task.cancel()
        self.current_task = asyncio.create_task(
            self._superviser(sequence_trigger, callback, *args, **kwargs)
        )

    async def _superviser(self, sequence_trigger, callback, *args, **kwargs):
        """Supervise the button when interrupt is enabled.

        Works by polling the button state; when not pressed counter is reset to 0; else
        makes it go up.

        Don't trigger the function at once to debounce. Also trigger when counter is *exactly*
        the amount requested so the function is called only once even if the button is
        pressed longer time.
        """
        polling = self.IRQ_POLLING

        logger.debug("Button {}: sleep until ready to start", self.name)
        while self.pressed:
            # sleep until the button is released so we can start waiting for it to be pressed
            await asyncio.sleep_ms(polling)

        burst = 0
        logger.debug("Button {}: starting supervision", self.name)
        while True:
            if self.pressed:
                burst += 1
                if burst == sequence_trigger:
                    break
                if burst > 1_000_000:
                    # just don't hit any integer limit
                    burst = sequence_trigger + 1
            else:
                # released, reset burst counter
                burst = 0
            await asyncio.sleep_ms(polling)

        logger.info("Button {}: callback!", self.name)
        await callback(*args, **kwargs)

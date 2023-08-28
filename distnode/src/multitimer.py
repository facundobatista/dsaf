# Copyright 2023 Facundo Batista
# https://github.com/facundobatista/dsaf

"""A multi-timer based on a unique hardware timer."""

from src import logger


# tick in milliseconds
TICK_DELAY = 200

# modes of working
ONE_SHOT = "oneshot"
PERIODIC = "periodic"
_mode_periodic = {
    ONE_SHOT: False,
    PERIODIC: True,
}

# collection of created timers
_timers = {}


def _ints_generator():
    """Infinite generator of integers."""
    value = 0
    while True:
        yield value
        value += 1


class Timer:
    """A single timer."""

    _get_timer_id = _ints_generator()

    def __init__(self):
        self._id = next(self._get_timer_id)

    def init(self, period, mode, callback):
        """Initiates the timer.

        Period is in milliseconds and must be a multiple of TICK_DELAY.
        """
        if self._id in _timers:
            raise RuntimeError("Attempted to init a timer while it was working.""")

        ticks_period, period_rest = divmod(period, TICK_DELAY)
        if period <= 0 or period_rest:
            raise ValueError("Period must be a positive multiple of TICK_DELAY")
        self.ticks_period = self.remaining_ticks = ticks_period

        try:
            self.is_periodic = _mode_periodic[mode]
        except KeyError:
            raise ValueError("Mode must be ONE_SHOT or PERIODIC")

        self.callback = callback
        _timers[self._id] = self

    def deinit(self):
        """Deactivate/disable/remove a timer."""
        _timers.pop(self._id, None)

    def _tick(self):
        """Tick this timer.

        This method should not be called manually, just use `tick` at module level to
        move all the timers machinery.
        """
        self.remaining_ticks -= 1
        if self.remaining_ticks:
            return

        # reset the counter if periodic; if oneshot just finish it
        if self.is_periodic:
            self.remaining_ticks = self.ticks_period
        else:
            self.deinit()

        # finally call the function
        try:
            self.callback(self)
        except Exception as exc:
            # inform the error but consume the exception otherwise will interrupt
            # the timers machinery
            logger.error("Error when calling callback from timer {}: {!r}", self._id, exc)


def tick():
    """Move the whole machinery.

    It must be called externally every TICK_DELAY (normally hooked into the
    microcontroller's hardware timer).
    """
    for timer in list(_timers.values()):
        timer._tick()

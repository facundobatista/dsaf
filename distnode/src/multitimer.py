# Copyright 2023 Facundo Batista
# https://github.com/facundobatista/dsaf

"""A multi-timer based on a unique hardware timer."""


def _timer_id_generator():
    value = 0
    while True:
        yield value
        value += 1


_get_timer_id = _timer_id_generator()


class _Timer:
    def __init__(self, is_periodic, ticks_period, callback):
        self.is_periodic = is_periodic
        self.ticks_period = self.remaining_ticks = ticks_period
        self.callback = callback
        self.timer_id = next(_get_timer_id)
        self.expired = False

    def tick(self):
        """Tick the timer."""
        self.remaining_ticks -= 1
        if self.remaining_ticks:
            return

        # time to call!
        try:
            self.callback(self.timer_id)
        except Exception as exc:
            # inform the error but consume the exception otherwise will interrupt
            # the timers machinery
            print(f"Error when calling callback from timer {self.timer_id}: {exc!r}")

        # if it was one shot now it's expired
        if not self.is_periodic:
            self.expired = True

        # else just reset the counter
        self.remaining_ticks = self.ticks_period


class MultiTimer:  # FIXME: not a class

    # tick in milliseconds
    TICK_DELAY = 100

    # modes of working
    ONE_SHOT = "oneshot"
    PERIODIC = "periodic"
    _mode_periodic = {
        ONE_SHOT: False,
        PERIODIC: True,
    }

    def __init__(self):
        self._timers = {}

    def init(self, period, mode, callback):
        """Initiates a timer.

        Period is in milliseconds and must be a multiple of TICK_DELAY.
        """
        tick_period, period_rest = divmod(period, self.TICK_DELAY)
        if period <= 0 or period_rest:
            raise ValueError("Period must be a positive multiple of TICK_DELAY")
        try:
            is_periodic = self._mode_periodic[mode]
        except KeyError:
            raise ValueError("Mode must be ONE_SHOT or PERIODIC")

        new_timer = _Timer(is_periodic, tick_period, callback)
        self._timers[new_timer.timer_id] = new_timer
        return new_timer.timer_id

    def deinit(self, timer_id):
        """Deactivate/disable/remove a timer."""
        oldtimer = self._timers.pop(timer_id, None)
        if oldtimer is None:
            raise ValueError(f"Tried to deinit a missing timer: {timer_id!r}")

    def tick(self):
        """Move the machinery.

        It must be called externally every TICK_DELAY (normally hooked into the
        microcontroller's hardware timer).
        """
        for timer in list(self._timers.values()):
            if not timer.expired:
                timer.tick()

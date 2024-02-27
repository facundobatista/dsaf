# Copyright 2023-2024 Facundo Batista
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


class Timer:
    """A single timer."""

    def __init__(self, name=None):
        if name is None:
            name = id(self)
        self._name = name

    def init(self, period, mode, callback):
        """Initiates the timer.

        Period is in milliseconds and must be a multiple of TICK_DELAY.
        """
        ticks_period, period_rest = divmod(period, TICK_DELAY)
        if period <= 0 or period_rest:
            raise ValueError("Period must be a positive multiple of TICK_DELAY")
        self._ticks_period = ticks_period

        try:
            self.is_periodic = _mode_periodic[mode]
        except KeyError:
            raise ValueError("Mode must be ONE_SHOT or PERIODIC")

        self.callback = callback
        _timer_manager.add(self, ticks_period)

    def deinit(self):
        """Deactivate/disable/remove a timer."""
        _timer_manager.remove(timer=self)

    def _run(self, idx):
        """Run the stored function and indicate if should continue to run."""
        if self.is_periodic:
            # will return own period to get called again in the future
            renovate = self._ticks_period
        else:
            # return None to not be re-scheduled and also remove from structures
            renovate = None
            _timer_manager.remove(idx=idx)

        # call the function
        try:
            self.callback(self)
        except Exception as exc:
            # inform the error but consume the exception otherwise will interrupt
            # the timers machinery
            logger.error("Error when calling callback from timer {}: {!r}", self._name, exc)

        return renovate


class _TimerManager:
    def __init__(self):
        # sequence of lists of two values: [[timer, remaining], ...], this structure
        # is paired on how it's used to minimize cost of using it
        self._timers_info = []

    def _iter_timers(self):
        """Iterate timer info from main structure filtering None.

        It iterates it not directly so the structure can grow while being iterated and
        it'll not get new ones in the iteration.
        """
        for idx in range(len(self._timers_info)):
            timerinfo = self._timers_info[idx]
            if timerinfo is not None:
                yield idx, timerinfo

    def remove(self, idx=None, timer=None):
        """Overwrite timer info in the structure.

        This can not be defragmented here, as it may happen while iterating structure.
        """
        if idx is None:
            for idx, (stored, _) in self._iter_timers():
                if stored is timer:
                    break
            else:
                return
        self._timers_info[idx] = None

    def add(self, timer, ticks_period):
        """Add a timer info to the structure.

        This can be done here as iteration when ticking support the structure to grow.
        """
        for _, (stored, _) in self._iter_timers():
            if stored is timer:
                raise RuntimeError("Attempted to init a timer while it was working.""")

        self._timers_info.append([timer, ticks_period])

    def tick(self):
        """Move the whole machinery.

        This algorithm is thought to minimize processing unless timer actually
        needs to be exercised; just try to do almost anything most of the times.
        """
        print("==== tick!", len(self._timers_info))
        for idx, timerinfo in self._iter_timers():
            # timerinfo is list of two values: [timer, remaining] -- we take advantage
            # of that here by just reducing remaining value without needing to re-store it
            timerinfo[1] -= 1

            if timerinfo[1]:
                # has remaining ticks
                continue

            # timer needs to be exercised!
            timer = timerinfo[0]
            renovated = timer._run(idx)

            # handle continuity
            if renovated:
                timerinfo[1] = renovated

        # defrag must only happen here (in any other place may happen while being iterated)
        self._timers_info[:] = [x for x in self._timers_info if x is not None]


class NonblockingLock:
    """A non blocking lock manually implemented."""

    def __init__(self):
        self._lock = {}

    def locked(self):
        """Return if lock is acquired."""
        return "" in self._lock

    def acquire(self):
        """Try to acquire the lock; return True if succeeded, False if not."""
        obj = object()
        stored = self._lock.setdefault("", obj)
        return obj is stored

    def release(self):
        """Release the lock; raise RuntimeError if was not locked."""
        try:
            del self._lock[""]
        except KeyError:
            raise RuntimeError("release not locked")


# manager to be ticked and a lock to not overlap
_tick_lock = NonblockingLock()
_timer_manager = _TimerManager()


def tick(_=None):
    """Handle not overlapping real ticking.

    It must be called externally every TICK_DELAY (normally hooked into the
    microcontroller's hardware timer).
    """
    free_to_go = _tick_lock.acquire()
    if not free_to_go:
        logger.error("Currently ticking!")
        return

    try:
        _timer_manager.tick()
    finally:
        _tick_lock.release()

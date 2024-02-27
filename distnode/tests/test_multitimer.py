# Copyright 2023-2024 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Tests for the multi timer."""

import pytest

from src import multitimer


class _CallCounter:
    """Helper to count calls."""

    def __init__(self):
        self.calls = []

    @property
    def total(self):
        """Return the count of total calls."""
        return len(self.calls)

    def __call__(self, timer):
        self.calls.append(timer)


@pytest.fixture
def call_counter():
    """Provide a _CallCounter instance."""
    return _CallCounter()


@pytest.fixture(autouse=True)
def structures_cleaner():
    """Automatically clean structures from any run test."""
    multitimer._timer_manager = multitimer._TimerManager()


def test_simple_oneshot_fast(call_counter):
    """Only one timer, one call, next one."""
    timer = multitimer.Timer()
    timer.init(period=multitimer.TICK_DELAY, mode=multitimer.ONE_SHOT, callback=call_counter)
    assert call_counter.total == 0

    multitimer.tick()
    assert call_counter.total == 1
    for _ in range(10):
        multitimer.tick()
    assert call_counter.total == 1


def test_simple_oneshot_later(call_counter):
    """Only one timer, one call, later."""
    timer = multitimer.Timer()
    timer.init(period=multitimer.TICK_DELAY * 3, mode=multitimer.ONE_SHOT, callback=call_counter)
    assert call_counter.total == 0

    multitimer.tick()
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 1
    for _ in range(10):
        multitimer.tick()
    assert call_counter.total == 1


def test_simple_periodic(call_counter):
    """Only one timer, periodic."""
    timer = multitimer.Timer()
    timer.init(period=multitimer.TICK_DELAY * 3, mode=multitimer.PERIODIC, callback=call_counter)
    assert call_counter.total == 0

    multitimer.tick()
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 1

    multitimer.tick()
    assert call_counter.total == 1
    multitimer.tick()
    assert call_counter.total == 1
    multitimer.tick()
    assert call_counter.total == 2

    multitimer.tick()
    assert call_counter.total == 2
    multitimer.tick()
    assert call_counter.total == 2
    multitimer.tick()
    assert call_counter.total == 3


def test_deinit_oneshot_before(call_counter):
    """Disable a timer before getting called."""
    timer = multitimer.Timer()
    timer.init(period=multitimer.TICK_DELAY * 3, mode=multitimer.ONE_SHOT, callback=call_counter)
    assert call_counter.total == 0

    multitimer.tick()
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 0

    timer.deinit()

    multitimer.tick()
    assert call_counter.total == 0
    for _ in range(10):
        multitimer.tick()
    assert call_counter.total == 0


def test_deinit_oneshot_after(call_counter):
    """Disable a one shot timer after being called (should be a no-op)."""
    timer = multitimer.Timer()
    timer.init(period=multitimer.TICK_DELAY * 2, mode=multitimer.ONE_SHOT, callback=call_counter)
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 1

    timer.deinit()

    for _ in range(10):
        multitimer.tick()
    assert call_counter.total == 1


def test_deinit_periodic(call_counter):
    """Disable a periodic timer."""
    timer = multitimer.Timer()
    timer.init(period=multitimer.TICK_DELAY * 2, mode=multitimer.PERIODIC, callback=call_counter)
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 1

    multitimer.tick()
    assert call_counter.total == 1

    timer.deinit()

    multitimer.tick()
    assert call_counter.total == 1
    for _ in range(10):
        multitimer.tick()
    assert call_counter.total == 1


def test_multiple_two_oneshots(call_counter):
    """Two one shots."""
    timer1 = multitimer.Timer()
    timer1.init(period=multitimer.TICK_DELAY * 2, mode=multitimer.ONE_SHOT, callback=call_counter)
    timer2 = multitimer.Timer()
    timer2.init(period=multitimer.TICK_DELAY * 5, mode=multitimer.ONE_SHOT, callback=call_counter)
    assert call_counter.calls == []

    multitimer.tick()
    assert call_counter.calls == []
    multitimer.tick()
    assert call_counter.calls == [timer1]

    multitimer.tick()
    assert call_counter.calls == [timer1]
    multitimer.tick()
    assert call_counter.calls == [timer1]
    multitimer.tick()
    assert call_counter.calls == [timer1, timer2]

    for _ in range(10):
        multitimer.tick()
    assert call_counter.calls == [timer1, timer2]


def test_multiple_two_periodics(call_counter):
    """Two periodics."""
    timer1 = multitimer.Timer()
    timer1.init(period=multitimer.TICK_DELAY * 2, mode=multitimer.PERIODIC, callback=call_counter)
    timer2 = multitimer.Timer()
    timer2.init(period=multitimer.TICK_DELAY * 5, mode=multitimer.PERIODIC, callback=call_counter)
    assert call_counter.calls == []

    multitimer.tick()
    assert call_counter.calls == []
    multitimer.tick()
    assert call_counter.calls == [timer1]

    multitimer.tick()
    assert call_counter.calls == [timer1]
    multitimer.tick()
    assert call_counter.calls == [timer1, timer1]

    multitimer.tick()
    assert call_counter.calls == [timer1, timer1, timer2]
    multitimer.tick()
    assert call_counter.calls == [timer1, timer1, timer2, timer1]


def test_multiple_mixed_with_deinit(call_counter):
    """Diverse combination."""
    timer1 = multitimer.Timer()
    timer1.init(period=multitimer.TICK_DELAY * 2, mode=multitimer.PERIODIC, callback=call_counter)
    timer2 = multitimer.Timer()
    timer2.init(period=multitimer.TICK_DELAY * 3, mode=multitimer.ONE_SHOT, callback=call_counter)
    timer3 = multitimer.Timer()
    timer3.init(period=multitimer.TICK_DELAY * 5, mode=multitimer.ONE_SHOT, callback=call_counter)
    assert call_counter.calls == []

    multitimer.tick()
    assert call_counter.calls == []
    multitimer.tick()
    assert call_counter.calls == [timer1]

    multitimer.tick()
    assert call_counter.calls == [timer1, timer2]
    multitimer.tick()
    assert call_counter.calls == [timer1, timer2, timer1]

    multitimer.tick()
    assert call_counter.calls == [timer1, timer2, timer1, timer3]
    timer1.deinit()
    multitimer.tick()
    assert call_counter.calls == [timer1, timer2, timer1, timer3]

    for _ in range(10):
        multitimer.tick()
    assert call_counter.calls == [timer1, timer2, timer1, timer3]


def test_reentrant_oneshot():
    """The timer is set again in the same function being called."""
    calls = []

    def callback(timer):
        calls.append(timer)
        if len(calls) == 1:
            timer.init(period=multitimer.TICK_DELAY, mode=multitimer.ONE_SHOT, callback=callback)

    timer = multitimer.Timer()
    timer.init(period=multitimer.TICK_DELAY, mode=multitimer.ONE_SHOT, callback=callback)

    multitimer.tick()
    assert calls == [timer]
    multitimer.tick()
    assert calls == [timer, timer]


def test_reentrant_deinit_oneshot():
    """The oneshot timer is deinited while being called."""
    calls = []

    def callback(timer):
        calls.append(timer)
        timer.deinit()

    timer = multitimer.Timer()
    timer.init(period=multitimer.TICK_DELAY, mode=multitimer.ONE_SHOT, callback=callback)

    multitimer.tick()
    assert calls == [timer]
    multitimer.tick()
    assert calls == [timer]


def test_reentrant_deinit_periodic():
    """The periodic timer is deinited while being called."""
    calls = []

    def callback(timer):
        calls.append(timer)
        timer.deinit()

    timer = multitimer.Timer()
    timer.init(period=multitimer.TICK_DELAY, mode=multitimer.PERIODIC, callback=callback)

    multitimer.tick()
    assert calls == [timer]
    multitimer.tick()
    assert calls == [timer]


# -- error cases

@pytest.mark.parametrize("period", [123.15, 0, -3])
def test_init_bad_period(period):
    """The period must be a multiple of constant tick."""
    timer = multitimer.Timer()
    with pytest.raises(ValueError):
        timer.init(period=period, mode=multitimer.ONE_SHOT, callback=None)


def test_init_bad_mode():
    """Bad mode."""
    timer = multitimer.Timer()
    with pytest.raises(ValueError):
        timer.init(period=multitimer.TICK_DELAY, mode="never", callback=None)


def test_init_twice():
    """Cannot init a timer twice."""
    timer = multitimer.Timer()
    timer.init(period=multitimer.TICK_DELAY, mode=multitimer.ONE_SHOT, callback=None)
    with pytest.raises(RuntimeError):
        timer.init(period=multitimer.TICK_DELAY, mode=multitimer.ONE_SHOT, callback=None)


def test_deinit_twice():
    """A deinit when not active should be a noop."""
    timer = multitimer.Timer()
    timer.init(period=multitimer.TICK_DELAY, mode=multitimer.ONE_SHOT, callback=None)
    timer.deinit()
    timer.deinit()


def test_init_deinit(call_counter):
    """The same timer can be re-inited."""
    timer = multitimer.Timer()
    timer.init(period=multitimer.TICK_DELAY, mode=multitimer.PERIODIC, callback=call_counter)
    assert call_counter.total == 0

    multitimer.tick()
    assert call_counter.total == 1
    multitimer.tick()
    assert call_counter.total == 2

    timer.deinit()

    multitimer.tick()
    multitimer.tick()
    multitimer.tick()
    assert call_counter.total == 2

    timer.init(period=multitimer.TICK_DELAY, mode=multitimer.PERIODIC, callback=call_counter)

    multitimer.tick()
    assert call_counter.total == 3
    multitimer.tick()
    assert call_counter.total == 4

    timer.deinit()

    multitimer.tick()
    assert call_counter.total == 4


def test_callback_robustness(logcheck):
    """Callback should always be called, even if fails sometimes."""
    calls_record = 0

    def the_callback(_):
        nonlocal calls_record
        calls_record += 1
        if calls_record == 3:
            raise ValueError("oops")

    timer = multitimer.Timer()
    timer.init(period=multitimer.TICK_DELAY, mode=multitimer.PERIODIC, callback=the_callback)
    assert calls_record == 0

    multitimer.tick()
    assert calls_record == 1
    multitimer.tick()
    assert calls_record == 2

    # this one will explode
    multitimer.tick()
    logcheck(f"Error when calling callback from timer {timer._name}: ValueError('oops')")
    assert calls_record == 3

    # life just goes on
    multitimer.tick()
    assert calls_record == 4


# -- tests for the lock

def test_lock_default():
    """Should be unlocked."""
    lock = multitimer.NonblockingLock()
    assert lock.locked() is False


def test_lock_sequence():
    """Basic acquire and release."""
    lock = multitimer.NonblockingLock()
    lock.acquire()
    assert lock.locked() is True
    lock.release()
    assert lock.locked() is False


def test_lock_double_acquire():
    """Try acquire twice (second should fail)."""
    lock = multitimer.NonblockingLock()
    assert lock.acquire() is True
    assert lock.locked() is True
    assert lock.acquire() is False  # didn't acquire
    assert lock.locked() is True
    lock.release()
    assert lock.locked() is False


def test_lock_():
    """Can't release an unlocked lock."""
    lock = multitimer.NonblockingLock()
    with pytest.raises(RuntimeError):
        lock.release()

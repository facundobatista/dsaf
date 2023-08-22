# Copyright 2023 Facundo Batista
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

    def __call__(self, timer_id):
        self.calls.append(timer_id)


@pytest.fixture
def call_counter():
    """Provide a _CallCounter instance."""
    return _CallCounter()


@pytest.fixture(autouse=True)
def timer_cleaner():
    """Automatically clean timers from any run test."""
    multitimer._timers.clear()


def test_simple_oneshot_fast(call_counter):
    """Only one timer, one call, next one."""
    period = multitimer.TICK_DELAY
    multitimer.init(period=period, mode=multitimer.ONE_SHOT, callback=call_counter)
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 1
    for _ in range(10):
        multitimer.tick()
    assert call_counter.total == 1


def test_simple_oneshot_later(call_counter):
    """Only one timer, one call, later."""
    period = multitimer.TICK_DELAY * 3
    multitimer.init(period=period, mode=multitimer.ONE_SHOT, callback=call_counter)
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
    period = multitimer.TICK_DELAY * 3
    multitimer.init(period=period, mode=multitimer.PERIODIC, callback=call_counter)
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
    period = multitimer.TICK_DELAY * 3
    timer_id = multitimer.init(period=period, mode=multitimer.ONE_SHOT, callback=call_counter)
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 0

    multitimer.deinit(timer_id)

    multitimer.tick()
    assert call_counter.total == 0
    for _ in range(10):
        multitimer.tick()
    assert call_counter.total == 0


def test_deinit_oneshot_after(call_counter):
    """Disable a one shot timer after being called (should be a no-op)."""
    period = multitimer.TICK_DELAY * 2
    timer_id = multitimer.init(period=period, mode=multitimer.ONE_SHOT, callback=call_counter)
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 1

    multitimer.deinit(timer_id)

    for _ in range(10):
        multitimer.tick()
    assert call_counter.total == 1


def test_deinit_periodic(call_counter):
    """Disable a periodic timer."""
    period = multitimer.TICK_DELAY * 2
    timer_id = multitimer.init(period=period, mode=multitimer.PERIODIC, callback=call_counter)
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 0
    multitimer.tick()
    assert call_counter.total == 1

    multitimer.tick()
    assert call_counter.total == 1

    multitimer.deinit(timer_id)

    multitimer.tick()
    assert call_counter.total == 1
    for _ in range(10):
        multitimer.tick()
    assert call_counter.total == 1


def test_multiple_two_oneshots(call_counter):
    """Two one shots."""
    period = multitimer.TICK_DELAY * 2
    timer_id_1 = multitimer.init(period=period, mode=multitimer.ONE_SHOT, callback=call_counter)
    period = multitimer.TICK_DELAY * 5
    timer_id_2 = multitimer.init(period=period, mode=multitimer.ONE_SHOT, callback=call_counter)

    assert call_counter.calls == []
    multitimer.tick()
    assert call_counter.calls == []
    multitimer.tick()
    assert call_counter.calls == [timer_id_1]

    multitimer.tick()
    assert call_counter.calls == [timer_id_1]
    multitimer.tick()
    assert call_counter.calls == [timer_id_1]
    multitimer.tick()
    assert call_counter.calls == [timer_id_1, timer_id_2]

    for _ in range(10):
        multitimer.tick()
    assert call_counter.calls == [timer_id_1, timer_id_2]


def test_multiple_two_periodics(call_counter):
    """Two periodics."""
    period = multitimer.TICK_DELAY * 2
    timer_id_1 = multitimer.init(period=period, mode=multitimer.PERIODIC, callback=call_counter)
    period = multitimer.TICK_DELAY * 5
    timer_id_2 = multitimer.init(period=period, mode=multitimer.PERIODIC, callback=call_counter)
    assert call_counter.calls == []

    multitimer.tick()
    assert call_counter.calls == []
    multitimer.tick()
    assert call_counter.calls == [timer_id_1]

    multitimer.tick()
    assert call_counter.calls == [timer_id_1]
    multitimer.tick()
    assert call_counter.calls == [timer_id_1, timer_id_1]

    multitimer.tick()
    assert call_counter.calls == [timer_id_1, timer_id_1, timer_id_2]
    multitimer.tick()
    assert call_counter.calls == [timer_id_1, timer_id_1, timer_id_2, timer_id_1]


def test_multiple_mixed_with_deinit(call_counter):
    """Diverse combination."""
    period = multitimer.TICK_DELAY * 2
    timer_id_1 = multitimer.init(period=period, mode=multitimer.PERIODIC, callback=call_counter)
    period = multitimer.TICK_DELAY * 3
    timer_id_2 = multitimer.init(period=period, mode=multitimer.ONE_SHOT, callback=call_counter)
    period = multitimer.TICK_DELAY * 5
    timer_id_3 = multitimer.init(period=period, mode=multitimer.ONE_SHOT, callback=call_counter)
    assert call_counter.calls == []

    multitimer.tick()
    assert call_counter.calls == []
    multitimer.tick()
    assert call_counter.calls == [timer_id_1]

    multitimer.tick()
    assert call_counter.calls == [timer_id_1, timer_id_2]
    multitimer.tick()
    assert call_counter.calls == [timer_id_1, timer_id_2, timer_id_1]

    multitimer.tick()
    assert call_counter.calls == [timer_id_1, timer_id_2, timer_id_1, timer_id_3]
    multitimer.deinit(timer_id_1)
    multitimer.tick()
    assert call_counter.calls == [timer_id_1, timer_id_2, timer_id_1, timer_id_3]

    for _ in range(10):
        multitimer.tick()
    assert call_counter.calls == [timer_id_1, timer_id_2, timer_id_1, timer_id_3]


@pytest.mark.parametrize("period", [123.15, 0, -3])
def test_init_bad_period(period):
    """Only one timer, one call, next one."""
    with pytest.raises(ValueError):
        multitimer.init(period=period, mode=multitimer.ONE_SHOT, callback=None)


def test_init_bad_mode():
    """Only one timer, one call, next one."""
    with pytest.raises(ValueError):
        multitimer.init(period=multitimer.TICK_DELAY, mode="never", callback=None)


def test_deinit_missing_timer_id():
    """Only one timer, one call, next one."""
    with pytest.raises(ValueError):
        multitimer.deinit(-1)


def test_deinit_twice():
    """Only one timer, one call, next one."""
    timer_id = multitimer.init(
        period=multitimer.TICK_DELAY, mode=multitimer.ONE_SHOT, callback=None)
    multitimer.deinit(timer_id)  # this first one should be ok
    with pytest.raises(ValueError):
        multitimer.deinit(timer_id)


def test_callback_robustness(logcheck):
    """Callback should always be called, even if fails sometimes."""
    calls_record = 0

    def the_callback(_):
        nonlocal calls_record
        calls_record += 1
        if calls_record == 3:
            raise ValueError("oops")

    timer_id = multitimer.init(
        period=multitimer.TICK_DELAY, mode=multitimer.PERIODIC, callback=the_callback)
    assert calls_record == 0
    multitimer.tick()
    assert calls_record == 1
    multitimer.tick()
    assert calls_record == 2

    # this one will explode
    multitimer.tick()
    logcheck(f"Error when calling callback from timer {timer_id}: ValueError('oops')")
    assert calls_record == 3

    # life just goes on
    multitimer.tick()
    assert calls_record == 4

# Copyright 2023 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Tests for the multi timer."""

import pytest

from src.multitimer import MultiTimer


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
    return _CallCounter()


def test_simple_oneshot_fast(call_counter):
    """Only one timer, one call, next one."""
    mt = MultiTimer()

    period = MultiTimer.TICK_DELAY
    mt.init(period=period, mode=MultiTimer.ONE_SHOT, callback=call_counter)
    assert call_counter.total == 0
    mt.tick()
    assert call_counter.total == 1
    for _ in range(10):
        mt.tick()
    assert call_counter.total == 1


def test_simple_oneshot_later(call_counter):
    """Only one timer, one call, later."""
    mt = MultiTimer()

    period = MultiTimer.TICK_DELAY * 3
    mt.init(period=period, mode=MultiTimer.ONE_SHOT, callback=call_counter)
    assert call_counter.total == 0
    mt.tick()
    assert call_counter.total == 0
    mt.tick()
    assert call_counter.total == 0
    mt.tick()
    assert call_counter.total == 1
    for _ in range(10):
        mt.tick()
    assert call_counter.total == 1


def test_simple_periodic(call_counter):
    """Only one timer, periodic."""
    mt = MultiTimer()

    period = MultiTimer.TICK_DELAY * 3
    mt.init(period=period, mode=MultiTimer.PERIODIC, callback=call_counter)
    assert call_counter.total == 0
    mt.tick()
    assert call_counter.total == 0
    mt.tick()
    assert call_counter.total == 0
    mt.tick()
    assert call_counter.total == 1

    mt.tick()
    assert call_counter.total == 1
    mt.tick()
    assert call_counter.total == 1
    mt.tick()
    assert call_counter.total == 2

    mt.tick()
    assert call_counter.total == 2
    mt.tick()
    assert call_counter.total == 2
    mt.tick()
    assert call_counter.total == 3


def test_deinit_oneshot_before(call_counter):
    """Disable a timer before getting called."""
    mt = MultiTimer()

    period = MultiTimer.TICK_DELAY * 3
    timer_id = mt.init(period=period, mode=MultiTimer.ONE_SHOT, callback=call_counter)
    assert call_counter.total == 0
    mt.tick()
    assert call_counter.total == 0
    mt.tick()
    assert call_counter.total == 0

    mt.deinit(timer_id)

    mt.tick()
    assert call_counter.total == 0
    for _ in range(10):
        mt.tick()
    assert call_counter.total == 0


def test_deinit_oneshot_after(call_counter):
    """Disable a one shot timer after being called (should be a no-op)."""
    mt = MultiTimer()

    period = MultiTimer.TICK_DELAY * 2
    timer_id = mt.init(period=period, mode=MultiTimer.ONE_SHOT, callback=call_counter)
    assert call_counter.total == 0
    mt.tick()
    assert call_counter.total == 0
    mt.tick()
    assert call_counter.total == 1

    mt.deinit(timer_id)

    for _ in range(10):
        mt.tick()
    assert call_counter.total == 1


def test_deinit_periodic(call_counter):
    """Disable a periodic timer."""
    mt = MultiTimer()

    period = MultiTimer.TICK_DELAY * 2
    timer_id = mt.init(period=period, mode=MultiTimer.PERIODIC, callback=call_counter)
    assert call_counter.total == 0
    mt.tick()
    assert call_counter.total == 0
    mt.tick()
    assert call_counter.total == 1

    mt.tick()
    assert call_counter.total == 1

    mt.deinit(timer_id)

    mt.tick()
    assert call_counter.total == 1
    for _ in range(10):
        mt.tick()
    assert call_counter.total == 1


def test_multiple_two_oneshots(call_counter):
    """Two one shots."""
    mt = MultiTimer()

    period = MultiTimer.TICK_DELAY * 2
    timer_id_1 = mt.init(period=period, mode=MultiTimer.ONE_SHOT, callback=call_counter)
    period = MultiTimer.TICK_DELAY * 5
    timer_id_2 = mt.init(period=period, mode=MultiTimer.ONE_SHOT, callback=call_counter)

    assert call_counter.calls == []
    mt.tick()
    assert call_counter.calls == []
    mt.tick()
    assert call_counter.calls == [timer_id_1]

    mt.tick()
    assert call_counter.calls == [timer_id_1]
    mt.tick()
    assert call_counter.calls == [timer_id_1]
    mt.tick()
    assert call_counter.calls == [timer_id_1, timer_id_2]

    for _ in range(10):
        mt.tick()
    assert call_counter.calls == [timer_id_1, timer_id_2]


def test_multiple_two_periodics(call_counter):
    """Two periodics."""
    mt = MultiTimer()

    period = MultiTimer.TICK_DELAY * 2
    timer_id_1 = mt.init(period=period, mode=MultiTimer.PERIODIC, callback=call_counter)
    period = MultiTimer.TICK_DELAY * 5
    timer_id_2 = mt.init(period=period, mode=MultiTimer.PERIODIC, callback=call_counter)
    assert call_counter.calls == []

    mt.tick()
    assert call_counter.calls == []
    mt.tick()
    assert call_counter.calls == [timer_id_1]

    mt.tick()
    assert call_counter.calls == [timer_id_1]
    mt.tick()
    assert call_counter.calls == [timer_id_1, timer_id_1]

    mt.tick()
    assert call_counter.calls == [timer_id_1, timer_id_1, timer_id_2]
    mt.tick()
    assert call_counter.calls == [timer_id_1, timer_id_1, timer_id_2, timer_id_1]


def test_multiple_mixed_with_deinit(call_counter):
    """Diverse combination."""
    mt = MultiTimer()

    period = MultiTimer.TICK_DELAY * 2
    timer_id_1 = mt.init(period=period, mode=MultiTimer.PERIODIC, callback=call_counter)
    period = MultiTimer.TICK_DELAY * 3
    timer_id_2 = mt.init(period=period, mode=MultiTimer.ONE_SHOT, callback=call_counter)
    period = MultiTimer.TICK_DELAY * 5
    timer_id_3 = mt.init(period=period, mode=MultiTimer.ONE_SHOT, callback=call_counter)
    assert call_counter.calls == []

    mt.tick()
    assert call_counter.calls == []
    mt.tick()
    assert call_counter.calls == [timer_id_1]

    mt.tick()
    assert call_counter.calls == [timer_id_1, timer_id_2]
    mt.tick()
    assert call_counter.calls == [timer_id_1, timer_id_2, timer_id_1]

    mt.tick()
    assert call_counter.calls == [timer_id_1, timer_id_2, timer_id_1, timer_id_3]
    mt.deinit(timer_id_1)
    mt.tick()
    assert call_counter.calls == [timer_id_1, timer_id_2, timer_id_1, timer_id_3]

    for _ in range(10):
        mt.tick()
    assert call_counter.calls == [timer_id_1, timer_id_2, timer_id_1, timer_id_3]


@pytest.mark.parametrize("period", [123.15, 0, -3])
def test_init_bad_period(period):
    """Only one timer, one call, next one."""
    mt = MultiTimer()
    with pytest.raises(ValueError):
        mt.init(period=period, mode=MultiTimer.ONE_SHOT, callback=None)


def test_init_bad_mode():
    """Only one timer, one call, next one."""
    mt = MultiTimer()
    with pytest.raises(ValueError):
        mt.init(period=MultiTimer.TICK_DELAY, mode="never", callback=None)


def test_deinit_missing_timer_id():
    """Only one timer, one call, next one."""
    mt = MultiTimer()
    with pytest.raises(ValueError):
        mt.deinit(-1)


def test_deinit_twice():
    """Only one timer, one call, next one."""
    mt = MultiTimer()
    timer_id = mt.init(period=MultiTimer.TICK_DELAY, mode=MultiTimer.ONE_SHOT, callback=None)
    mt.deinit(timer_id)  # this first one should be ok
    with pytest.raises(ValueError):
        mt.deinit(timer_id)


def test_callback_robustness(capsys):
    """Callback should always be called, even if fails sometimes."""
    mt = MultiTimer()

    calls_record = 0

    def the_callback(_):
        nonlocal calls_record
        calls_record += 1
        if calls_record == 3:
            raise ValueError("oops")

    mt.init(period=MultiTimer.TICK_DELAY, mode=MultiTimer.PERIODIC, callback=the_callback)
    assert calls_record == 0
    mt.tick()
    assert calls_record == 1
    mt.tick()
    assert calls_record == 2

    # this one will explode
    mt.tick()
    captured = capsys.readouterr()
    assert captured.out == "Error when calling callback from timer 0: ValueError('oops')\n"
    assert calls_record == 3

    # life just goes on
    mt.tick()
    assert calls_record == 4

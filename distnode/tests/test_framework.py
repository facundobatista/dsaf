# Copyright 2023 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Tests for the framework of the distributed node."""

from src.framework import FrameworkFSM


# -- tests for the Framework FSM

def test_consistency_all_functions_implemented():
    """All the functions defined in the transitions are implemented."""
    for _, method_name in FrameworkFSM._transitions.values():
        assert hasattr(FrameworkFSM, method_name)


def test_consistency_leds_complete():
    """All states have leds status defined for green and blue."""
    used_states = {state for state, _ in FrameworkFSM._transitions.values()}
    for state in used_states:
        assert len(FrameworkFSM._leds_status[state]) == 2


def test_consistency_leds_definition():
    """If led blinks, has a sequence of on/off multiple of 100ms, else its boolean."""
    for statuses in FrameworkFSM._leds_status.values():
        for shall_blink, value in statuses:
            if shall_blink:
                assert len(value) % 2 == 0
                for delay in value:
                    assert delay % 100 == 0
            else:
                assert value in (True, False)

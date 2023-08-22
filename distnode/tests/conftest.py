# Copyright 2023 Facundo Batista
# https://github.com/facundobatista/dsaf

import time

import pytest


@pytest.fixture(scope="module", autouse=True)
def fix_time():
    """Patch time module with needed attribute to run tests outside microcontroller."""
    if not hasattr(time, "ticks_ms"):
        time.ticks_ms = lambda: int(time.time() * 1000)


@pytest.fixture()
def logcheck(capsys):

    def _f(should):
        captured = capsys.readouterr()
        for line in captured.out.split("\n"):
            if should in line:
                return
        pytest.fail("Line not in stdout")

    return _f

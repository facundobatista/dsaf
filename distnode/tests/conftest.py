# Copyright 2023 Facundo Batista
# https://github.com/facundobatista/dsaf

import asyncio
import sys
import urllib
import urllib.request

import pytest

from tests.fakemods import network


# fix imports and names for micropython universe
sys.modules["uasyncio"] = asyncio
sys.modules["network"] = network
urllib.urequest = urllib.request


@pytest.fixture()
def logcheck(capsys):

    def _f(should):
        captured = capsys.readouterr()
        for line in captured.out.split("\n"):
            if should in line:
                return
        pytest.fail("Line not in stdout")

    return _f

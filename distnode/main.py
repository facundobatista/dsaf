# Copyright 2023-2024 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Microcontroller's entry point."""

import uasyncio

from src import main
uasyncio.run(main.run())

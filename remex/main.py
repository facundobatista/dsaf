# Copyright 2025 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Microcontroller's entry point."""

import asyncio

from src import main


async def waiter():
    await asyncio.sleep(60)
    main.breath()

loop = asyncio.get_event_loop()
asyncio.create_task(main.run())
while True:
    loop.run_until_complete(waiter())

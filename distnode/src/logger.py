# Copyright 2023 Facundo Batista
# https://github.com/facundobatista/dsaf

import time


def _log(template, *params):
    """Print the requested text with a timestamp prefix."""
    ticks = str(time.ticks_ms())
    sec, ms = ticks[:-3], ticks[-3:]
    text = template.format(*params)
    print(f"{sec:>8s}.{ms}  {text}")


def info(template, *params):
    # XXX validate level
    _log(template, *params)


def debug(template, *params):
    # XXX validate level
    _log(template, *params)

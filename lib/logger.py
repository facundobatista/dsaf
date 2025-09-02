# Copyright 2025 Facundo Batista
# https://github.com/facundobatista/dsaf/

import time

# adaptation layer for the module to be used in regular Python
if not hasattr(time, "ticks_ms"):
    time.ticks_ms = lambda: int(time.time() * 1000)


# levels
DEBUG = 10
INFO = 20
ERROR = 30

# default
_level = ERROR


def set_level(level):
    global _level
    _level = level


def _log(level, template, *params):
    """Print the requested text with a timestamp prefix."""
    ticks = str(time.ticks_ms())
    sec, ms = ticks[:-3], ticks[-3:]
    try:
        text = template.format(*params)
    except Exception as err:
        print("~~~ ERROR building log line!", repr(template), params, repr(err))
    else:
        print(f"{sec:>8s}.{ms} {level}  {text}")


def error(template, *params):
    if _level <= ERROR:
        _log("ERROR", template, *params)


def info(template, *params):
    if _level <= INFO:
        _log("INFO ", template, *params)


def debug(template, *params):
    if _level <= DEBUG:
        _log("DEBUG", template, *params)

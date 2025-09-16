# Copyright 2025 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Utilities related to dealing with time."""

import time

from lib import logger

try:
    from machine import RTC
except ImportError:
    RTC = None


def set_time_from_dict(ct):
    """Set microcontroller's time.

    Note that we avoid using `subseconds` because its meaning is hardware dependent.
    """
    rtc = RTC()
    time_tuple = (
        ct["year"],
        ct["month"],
        ct["day"],
        ct["weekday"],
        ct["hours"],
        ct["minutes"],
        ct["seconds"],
        0,
    )
    logger.debug("Set device time to {}", time_tuple)
    rtc.datetime(time_tuple)


def get_gmtime_as_dict():
    """Get the time in UTC as a dict.

    This is multiplatform.
    """
    if RTC is None:
        # not micropython; standard Python interface
        ct = time.gmtime()
        year = ct.tm_year
        month = ct.tm_mon
        day = ct.tm_mday
        hours = ct.tm_hour
        minutes = ct.tm_min
        seconds = ct.tm_sec
        weekday = ct.tm_wday

    else:
        # micropython! here we use `RTC.datetime` just for consistency; mixing it with
        # `time.gmtime` is error prone: even if values are the same, they are in different order!
        rtc = RTC()
        year, month, day, weekday, hours, minutes, seconds, _ = rtc.datetime()

    return {
        "year": year,
        "month": month,
        "day": day,
        "weekday": weekday,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
    }


def nice_time():
    """Return the current time in a nice format."""
    ct = get_gmtime_as_dict()
    return "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(
        ct["year"],
        ct["month"],
        ct["day"],
        ct["hours"],
        ct["minutes"],
        ct["seconds"],
    )

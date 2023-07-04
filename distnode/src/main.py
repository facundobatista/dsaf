# Copyright 2023 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Distributed node framework."""

import json
import time
from urllib import urequest

import machine
import network

import logger
from framework import FrameworkFSM
from sensor import ExampleSensorManager


timer = machine.Timer(-1)


class Led:
    """Manage a led."""

    def __init__(self, pin_id):
        self.led = machine.Pin(2, machine.Pin.OUT)  # "active low"; IOW "inversed"
        self.blink_idx = None
        self.blink_on = None

    def set(self, on):
        """Turn on (on=True) or off (on=False) the led permanently."""
        # note the led is inversed!!
        if on:
            self.led.off()
        else:
            self.led.on()

    def blink(self, delays_sequence):
        """Blink the led, passing some time on, then some time off, loop.

        Accepts any sequence of delays, starting with "time in on", with two restrictions:
        - time in milliseconds
        - the sequence must be of even quantity of values
        """
        # cancel any previous blinking
        timer.deinit()

        self.blink_on = False  # starts with ligth on (inversed!)
        self.blink_idx = 0

        def _step(_):
            if self.blink_on:
                self.led.on()
            else:
                self.led.off()
            delay = delays_sequence[self.blink_idx]

            self.blink_on = not self.blink_on
            self.blink_idx += 1
            if self.blink_idx == len(delays_sequence):
                self.blink_idx = 0

            timer.init(period=delay, mode=machine.Timer.ONE_SHOT, callback=_step)

        _step(None)


# XXX: to be used in the future
# def send_status(_):
#     """Send status information to the server."""
#     # prepare the status
#     payload = {"foo": 3}  # XXX: better info! ping time to server and current datetime
#
#     # send it to the manager
#     url = "http://{manager-host}:{manager-port}/v1/status/".format_map(config)
#     encoded_payload = json.dumps(payload).encode("ascii")
#     req = request.Request(url, method="POST", data=encoded_payload, headers=JSON_CT)
#     request.urlopen(req)  # XXX support errors here


class NetworkManager:
    def __init__(self):
        self.ssid = None
        self.password = None
        self.wlan = None

    def connect(self, ssid, password):
        """Connect to the network."""
        logger.info("NetworkManager: connect")
        self.ssid = ssid
        self.password = password

        if self.wlan is not None and self.wlan.isconnected():
            logger.debug("NetworkManager: already connected, disconnecting...")
            self.wlan.disconnect()

        self.wlan = network.WLAN(network.STA_IF)  # create station interface
        self.wlan.active(True)  # activate the interface
        self.wlan.connect(self.ssid, self.password)
        while not self.wlan.isconnected():
            logger.debug("NetworkManager: waiting for connection...")
            time.sleep(1)
        logger.info("NetworkManager: connected!", self.wlan.ifconfig())

    def hit(self, url, payload):
        """Do a POST to an url with a json-able payload."""
        logger.debug("Network hit {} with {}", url, payload)
        data = json.dumps(payload).encode("ascii")
        try:
            resp = urequest.urlopen(url, data=data)
        except OSError as exc:
            if exc.errno == 103:
                logger.debug("Network connection lost")
                # connection broken, reconnect and retry
                self.connect(self.ssid, self.password)
                resp = urequest.urlopen(url, data=data)
            else:
                raise

        content = resp.read()
        resp.close()
        return content


logger.info("Start")
# XXX: use an external led for this!
green_led = Led(2)

fsm = FrameworkFSM(NetworkManager(), ExampleSensorManager, green_led)
fsm.loop()

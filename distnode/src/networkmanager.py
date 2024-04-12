# Copyright 2023-2024 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Network usage layer."""

import json
import uasyncio
from urllib import urequest

import network

from src import logger


class NetworkError(Exception):
    """Generic network error."""


class NetworkManager:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.wlan = None
        self.connected = False

    async def connect(self):
        """Connect to the network."""
        logger.info("NetworkManager: connect")

        if self.wlan is not None and self.wlan.isconnected():
            logger.debug("NetworkManager: already connected, disconnecting...")
            self.wlan.disconnect()

        self.wlan = network.WLAN(network.STA_IF)  # create station interface
        self.wlan.active(True)  # activate the interface
        self.wlan.connect(self.ssid, self.password)
        while not self.wlan.isconnected():
            logger.debug("NetworkManager: waiting for connection...")
            await uasyncio.sleep_ms(1000)
        self.connected = True
        logger.info("NetworkManager: connected! {}", self.wlan.ifconfig())

    async def hit(self, url, payload):
        """Do a POST to an url with a json-able payload."""
        if not self.connected:
            await self.connect()

        logger.debug("Network hit {} with {}", url, payload)
        data = json.dumps(payload).encode("ascii")
        try:
            resp = urequest.urlopen(url, data=data)
        except OSError as exc:
            if exc.errno == 103:
                logger.debug("Network connection lost")
                self.connected = False
            elif exc.errno == 104:
                logger.debug("Server not available")
            else:
                logger.debug("Network unknown OSError: {}", exc.errno)
                raise
            raise NetworkError()

        content = resp.read()
        resp.close()
        return content

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
        self.connection_lock = uasyncio.Lock()

    async def connect(self):
        """Connect to the network."""
        logger.info("NetworkManager: connect?")
        if self.connected:
            logger.info("NetworkManager: already connected, done")
            return
        logger.info("NetworkManager: connect!")

        # support for confused hardware state
        if self.wlan is not None and self.wlan.isconnected():
            logger.debug("NetworkManager: underlying already connected, disconnecting...")
            self.wlan.disconnect()

        # create station interface, activate, and connect
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.connect(self.ssid, self.password)

        # wait until connection is fully established
        while not self.wlan.isconnected():
            logger.debug("NetworkManager: waiting for connection...")
            await uasyncio.sleep_ms(500)
        self.connected = True
        logger.info("NetworkManager: connected! {}", self.wlan.ifconfig())

    async def hit(self, url, payload):
        """Do a POST to an url with a json-able payload."""
        logger.debug("NetworkManager: hit {} with {}", url, payload)

        if not self.connected:
            async with self.connection_lock:
                await self.connect()

        data = json.dumps(payload).encode("ascii")
        try:
            resp = urequest.urlopen(url, data=data)
        except OSError as exc:
            logger.debug("NetworkManager: urlopen oserror: {}", exc.errno)
            if exc.errno == 103:
                # disconnection
                self.connected = False
            elif exc.errno == 104:
                # normal server down
                pass
            else:
                logger.error("Network unknown OSError: {}", exc.errno)
                raise
            raise NetworkError(str(exc))

        content = resp.read()
        resp.close()
        return content

# Copyright 2025 Facundo Batista
# https://github.com/facundobatista/dsaf/

"""Network usage layer."""

import asyncio

import network

from src import logger

# turn off the AP on boot, it's handled properly by code
network.WLAN(network.AP_IF).active(False)


class NetworkError(Exception):
    """Generic network error."""


class NetworkManager:
    """A layer to simplify using the network as Access Point or to connect to one."""

    def __init__(self):
        self.wlan = None
        self.connected = False
        self.connection_lock = asyncio.Lock()
        self.ap = None

    async def start_ap(self, ssid, password):
        """Start the access point."""
        if self.wlan is not None:
            raise ValueError("NetworkManager error, trying to start AP while working with WLAN")

        logger.info("NetworkManager: starting AP")
        self.ap = network.WLAN(network.AP_IF)
        self.ap.active(True)

        while not self.ap.active():
            logger.debug("NetworkManager: waiting to activate...")
            await asyncio.sleep_ms(500)

        self.ap.config(ssid=ssid, password=password)  # need to be after active
        logger.info("NetworkManager: AP up")

    async def stop(self):
        """Stop any network usage."""
        if self.ap is not None:
            self.ap.active(False)

            while self.ap.active():
                logger.debug("NetworkManager: waiting to shutdown...")
                await asyncio.sleep_ms(500)
            self.ap = None
            logger.info("NetworkManager: AP down")

        if self.wlan is not None and self.wlan.isconnected():
            self.wlan.disconnect()
            self.wlan = None
            logger.info("NetworkManager: WLAN off")

    async def connect(self, ssid, password):
        """Connect to the network."""
        if self.ap is not None:
            raise ValueError("NetworkManager error, trying to start WLAN while working as an AP")

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
        self.wlan.connect(ssid, password)

        # wait until connection is fully established
        while not self.wlan.isconnected():
            logger.debug("NetworkManager: waiting for connection...")
            await asyncio.sleep_ms(500)
        self.connected = True
        logger.info("NetworkManager: connected! {}", self.wlan.ifconfig())

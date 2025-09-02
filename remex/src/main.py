# Copyright 2025 Facundo Batista
# https://github.com/facundobatista/dsaf/

"""Main device code."""

import gc
import json
import os
import time

import machine

from lib.comms import ProtocolServer, ProtocolClient, STATUS_OK
from lib import logger
from src.button import Button
from src.outputs import Led
from src.networkmanager import NetworkManager

# used pins
PIN_FLASH_BUTTON = 0
PIN_POWER_LED = 2
PIN_STATUS_LED = 16

# set of blinkings
BLINK_POWER_OK = [100, 9900]
BLINK_POWER_PANIC = [260, 240]
BLINK_STATUS_BAD_CONFIG = [200, 2800]
BLINK_STATUS_BAD_WIFI = [200, 200, 200, 2400]
BLINK_STATUS_BAD_CONNECTION = [200, 200, 200, 200, 200, 2000]
BLINK_STATUS_REJECTED = [200, 200, 200, 200, 200, 200, 200, 1600]


class Storage:
    def __init__(self, filepath):
        self._filepath_temp = filepath + ".temp"
        try:
            os.stat(self._filepath_temp)
        except OSError:
            pass
        else:
            logger.warning("Found temporal storage file!")

        self._filepath = filepath
        try:
            with open(filepath, "rt") as fh:
                self._storage = json.load(fh)
        except OSError:
            self._storage = {}

    def exists(self):
        """Indicate if there is *any* config."""
        return self._storage != {}

    def get(self, key, default=None):
        """Return the value of the key in the storage, default if not present."""
        return self._storage.get(key, default)

    def _save(self):
        """Securely save to disk."""
        with open(self._filepath_temp, "wt") as fh:
            json.dump(self._storage, fh)
        os.rename(self._filepath_temp, self._filepath)

    def update(self, source):
        """Set and save the multiple key/value pairs in the storage."""
        self._storage.update(source)
        self._save()

    def set(self, key, value):
        """Set and save the key/value pair in the storage."""
        self._storage[key] = value
        self._save()


class SystemBoard:
    def __init__(self):
        self.config = Storage("remex-config.db")
        self.protocol_server = None
        self.network_manager = None

        self.status_led = Led(PIN_STATUS_LED, inverted=True)
        self.power_led = Led(PIN_POWER_LED, inverted=True)
        self.button = Button(PIN_FLASH_BUTTON)

    async def run(self):
        """Start to work the main system."""
        # blink leds to indicate we started working
        await self.status_led.blink_once([100, 500, 100, 100, 100, 500])
        await self.enter_regular_mode()

    async def _close_current_servers(self):
        """Close/stop current servers/managers."""
        logger.debug("Cycling servers! free mem before: {}", gc.mem_free())
        if self.network_manager is not None:
            logger.info("Stopping previous network manager")
            await self.network_manager.stop()
            self.network_manager = None
        if self.protocol_server is not None:
            logger.info("Stopping previous http server")
            await self.protocol_server.close()
            self.protocol_server = None
        gc.collect()
        logger.debug("Cycling servers! free mem after:  {}", gc.mem_free())

    @property
    def health(self):
        """Build a set of data representing the status of the device/framework."""
        mem_free = gc.mem_free()
        current_time = time.gmtime()
        configured = self.config.exists()
        return dict(mem_free=mem_free, current_time=current_time, configured=configured)

    async def _serve_health(self):
        """Report the general health of the device."""
        print("=================== SERVE HEALTH")
        return json.dumps(self.health)

    async def _serve_config(self, raw_data):
        """Receive and save config."""
        print("=================== SERVE CONFIG", raw_data)
        # wifi (ssid y clave), ip del management node, nombre device, hora *posta*
        info = json.loads(raw_data)

        # set microcontroller's time
        time_tuple = info.pop("current_time_tuple")[:8]  # discard DST, if came
        rtc = machine.RTC()
        rtc.datetime(time_tuple)

        # check arrived info and save config
        assert set(info) == {"wifi_ssid", "wifi_password", "management_node_ip", "name"}
        self.config.update(info)
        logger.info("Saved new configuration")

    async def enter_config_mode(self):
        """Configuration mode.

        - set led to blinking
        - change button to callback to regular mode
        """
        logger.info("Entering Config mode")
        await self._close_current_servers()
        self.status_led.set(True)
        self.power_led.start_blinking([500, 500])
        self.button.set_interrupt(200, self.enter_regular_mode)
        print("=================== MODE CONFIG")

        # open wifi
        ssid = "Remex-" + machine.unique_id().hex()
        self.network_manager = NetworkManager()
        await self.network_manager.start_ap(ssid, "remex-config")
        print("=================== wifi ok")

        # views_handler = ViewsHandler(self.storage)
        callbacks = {
            "HEALTH": self._serve_health,
            "CONFIG": self._serve_config,
        }
        self.protocol_server = ProtocolServer(callbacks)
        await self.protocol_server.listen(80)
        logger.info("Serving config")

    async def _update_job(self, data):
        """Receive a new job to run."""
        print("=================== UPDATE JOB!!!", repr(data))

    async def enter_regular_mode(self):
        """Regular operation mode."""
        logger.info("Entering Regular mode")
        await self._close_current_servers()
        self.button.set_interrupt(2500, self.enter_config_mode)

        print("=================== MODE REGULAR")

        # get required info from the config
        if not self.config.exists():
            self.power_led.start_blinking(BLINK_POWER_PANIC)
            self.status_led.start_blinking(BLINK_STATUS_BAD_CONFIG)
            logger.error("Missing config")
            return

        info = {}
        for key in ["wifi_ssid", "wifi_password", "management_node_ip", "name"]:
            value = self.config.get(key)
            if value is None:
                self.power_led.start_blinking(BLINK_POWER_PANIC)
                self.status_led.start_blinking(BLINK_STATUS_BAD_CONFIG)
                logger.error("Missing {!r} key in the config", key)
                return
            info[key] = value

        logger.debug("Connecting to WiFi")
        self.network_manager = NetworkManager()
        try:
            await self.network_manager.start_ap(info["wifi_ssid"], info["wifi_password"])
        except Exception as exc:
            self.power_led.start_blinking(BLINK_POWER_PANIC)
            self.status_led.start_blinking(BLINK_STATUS_BAD_WIFI)
            logger.error("Problem starting the AP: {!r}", exc)
            return

        logger.debug("Connecting to Management node")
        client = ProtocolClient(info["name"], callbacks={"UPDATE-JOB": self._update_job})
        try:
            await client.connect(info["management_node_ip"], 443)
        except Exception as exc:
            self.power_led.start_blinking(BLINK_POWER_PANIC)
            self.status_led.start_blinking(BLINK_STATUS_BAD_CONNECTION)
            logger.error("Problem connecting to the Management node: {!r}", exc)
            return

        status, content = await client.request("CHECK-IN", json.dumps(self.health))
        if status != STATUS_OK:
            self.power_led.start_blinking(BLINK_POWER_PANIC)
            self.status_led.start_blinking(BLINK_STATUS_REJECTED)
            logger.error("Failed to check in; response: {!r}", content)
            return

        # all good, set leds to indicate the device is up and running just fine
        self.status_led.set(False)
        self.power_led.start_blinking(BLINK_POWER_OK)


system_board = SystemBoard()


async def run():
    logger.set_level(logger.DEBUG)
    logger.info("Start, base mem: {} - time: {}", gc.mem_free(), time.gmtime())
    await system_board.run()


def breath():
    gc.collect()
    logger.debug("Breathing... free mem: {} - time: {}", gc.mem_free(), time.gmtime())

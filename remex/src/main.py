# Copyright 2025 Facundo Batista
# https://github.com/facundobatista/dsaf/

"""Main device code."""

import asyncio
import gc
import json
import os
import time

import machine

from lib import logger
from lib.comms import ProtocolServer, ProtocolClient, STATUS_OK
from lib.time_utils import get_gmtime_as_dict, set_time_from_dict, nice_time
from src.button import Button
from src.networkmanager import NetworkManager
from src.outputs import Led

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

# where the code to run is stored
JOB_FILENAME = "externalcode.py"

# how many seeconds between connection checks
CONNECTION_ALIVE_POLL_SECS = 5

logger.set_level(logger.DEBUG)


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
        logger.debug("Current config: {}", self._storage)

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
        self.config_server = None
        self.network_manager = None
        self.current_job_task = None
        self.management_client = None

        self.status_led = Led(PIN_STATUS_LED, inverted=True)
        self.power_led = Led(PIN_POWER_LED, inverted=True)
        self.button = Button(PIN_FLASH_BUTTON)

    async def run(self):
        """Start to work the main system."""
        # blink leds to indicate we started working
        await self.status_led.blink_once([100, 500, 100, 100, 100, 500])

        if self.button.pressed:
            # go directly to config (very useful when user's job blocks regular work)
            await self.enter_regular_mode
        else:
            await self.enter_regular_mode()

    async def _stop_current_processes(self):
        """Close/stop current servers/managers/jobs."""
        logger.debug("Cycling processes! free mem before: {}", gc.mem_free())

        if self.network_manager is not None:
            logger.info("Stopping previous network manager")
            await self.network_manager.stop()
            self.network_manager = None

        if self.config_server is not None:
            logger.info("Stopping previous config server")
            await self.config_server.close()
            self.config_server = None

        if self.management_client is not None:
            logger.info("Stopping previous management_client")
            await self.management_client.close()
            self.management_client = None

        self._stop_job()

        gc.collect()
        logger.debug("Cycling servers! free mem after:  {}", gc.mem_free())

    @property
    def health(self):
        """Build a set of data representing the status of the device/framework."""
        mem_free = gc.mem_free()
        current_time = get_gmtime_as_dict()
        configured = self.config.exists()
        return dict(mem_free=mem_free, current_time=current_time, configured=configured)

    async def _serve_health(self, _):
        """Report the general health of the device."""
        return json.dumps(self.health)

    async def _serve_config(self, _, raw_data):
        """Receive and save config."""
        # wifi (ssid y clave), ip del management node, nombre device, hora *posta*
        info = json.loads(raw_data)

        set_time_from_dict(info.pop("current_time"))

        # check arrived info and save config
        if set(info) != {"wifi_ssid", "wifi_password", "management_node_ip", "name"}:
            raise ValueError(f"Invalid data received to config: {info}")

        self.config.update(info)
        logger.info("Saved new configuration")

    async def enter_config_mode(self):
        """Configuration mode.

        - set led to blinking
        - change button to callback to regular mode
        """
        logger.info("Entering Config mode")
        await self._stop_current_processes()
        self.status_led.set(True)
        self.power_led.start_blinking([500, 500])
        self.button.set_interrupt(200, self.enter_regular_mode)

        # open wifi
        ssid = "Remex-" + machine.unique_id().hex()
        self.network_manager = NetworkManager()
        await self.network_manager.start_ap(ssid, "remex-config")

        callbacks = {
            "HEALTH": self._serve_health,
            "CONFIG": self._serve_config,
        }
        self.config_server = ProtocolServer(callbacks)
        await self.config_server.listen(80)
        logger.info("Serving config")

    async def _connect_to_management_node(self, info):
        """Connect to the network & the management service, return if connection was successful."""
        logger.debug("Connecting to WiFi")
        self.network_manager = NetworkManager()
        try:
            await self.network_manager.connect(info["wifi_ssid"], info["wifi_password"])
        except Exception as exc:
            self.power_led.start_blinking(BLINK_POWER_PANIC)
            self.status_led.start_blinking(BLINK_STATUS_BAD_WIFI)
            logger.error("Problem connecting to WiFi: {!r}", exc)
            return

        logger.debug("Connecting to Management node")
        callbacks = {
            "UPDATE-JOB": self._update_job,
            "GET-JOB": self._get_job,
        }
        client = ProtocolClient(info["name"], callbacks=callbacks)
        try:
            await client.connect(info["management_node_ip"], 7739)
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
        info = json.loads(content)
        set_time_from_dict(info["current_time"])

        # all good, set leds to indicate the device is up and running just fine
        logger.info("Connected to Management node! Check-in OK")
        self.status_led.set(False)
        self.power_led.start_blinking(BLINK_POWER_OK)

        return client

    async def _connect_to_server(self):
        """Get to WiFi and connect to the server (and retry if something is wrong).

        This keeps a "connected" attribute, so the breathing knows what it can do.
        """
        if self.management_client:
            raise ValueError("Connect to server called while connected!")

        # get required info from the config
        if not self.config.exists():
            self.power_led.start_blinking(BLINK_POWER_PANIC)
            self.status_led.start_blinking(BLINK_STATUS_BAD_CONFIG)
            logger.error("Missing config")
            # there is no retry possible on this
            return

        info = {}
        for key in ["wifi_ssid", "wifi_password", "management_node_ip", "name"]:
            value = self.config.get(key)
            if value is None:
                self.power_led.start_blinking(BLINK_POWER_PANIC)
                self.status_led.start_blinking(BLINK_STATUS_BAD_CONFIG)
                logger.error("Missing {!r} key in the config", key)
                # there is no retry possible on this
                return
            info[key] = value

        # this is a forever loop that will keep getting connected to the management node no
        # matter what (as it's the only way to remotely report)
        while True:
            logger.debug("Server connection loop: starting...")
            try:
                # connect...
                client = await self._connect_to_management_node(info)
                self.management_client = client
                logger.debug("Server connection loop: connected? {}", client is not None)

                # ...and suppervise the connection
                while True:
                    tini = time.ticks_ms()
                    status, content = await client.request("PING")
                    if status != STATUS_OK or content != b"PONG":
                        raise ValueError(f"Got bad PONG: status={status!r} content={content!r}")
                    tend = time.ticks_ms()
                    logger.debug("Server connection loop: ping time {} ms", tend - tini)
                    await asyncio.sleep(CONNECTION_ALIVE_POLL_SECS)
            except Exception as err:
                self.management_client = None
                logger.error("Server connection loop: problem! {!r}", err)
            await asyncio.sleep(CONNECTION_ALIVE_POLL_SECS)

    async def _run_current_job(self):
        """Run current job, if any."""
        try:
            with open(JOB_FILENAME, "rb") as fh:
                code = fh.read()
        except OSError:
            logger.error("No code to run")
        else:
            self._start_job(code)

    async def enter_regular_mode(self):
        """Regular operation mode."""
        logger.info("Entering Regular mode")
        await self._stop_current_processes()
        self.button.set_interrupt(2000, self.enter_config_mode)

        await asyncio.gather(
            self._connect_to_server(),
            self._run_current_job(),
        )

    def _stop_job(self):
        """Stop current job, if any."""
        if self.current_job_task is None:
            return

        logger.info("Stopping old job")
        tini = time.ticks_ms()
        try:
            result = self.current_job_task.cancel()
        except Exception as exc:
            error = repr(exc)
            logger.error("Stopped in error: {!r}", exc)
        else:
            error = None
            logger.info("Stopped ok; was still active?: {}", result)
        tend = time.ticks_ms()
        return {"error": error, "delay_ms": tend - tini}

    def _start_job(self, code):
        """Start a job."""
        logger.info("Processing code, importing main function")
        status = {}

        tini = time.ticks_ms()
        try:
            fake_module = {}
            exec(code, fake_module)
            job_coroutine = fake_module["run"]
        except Exception as exc:
            error = repr(exc)
            logger.error("Processing up ended in error: {!r}", exc)
        else:
            error = None
            logger.info("Processing ended ok")
        tend = time.ticks_ms()
        status["setup"] = {"error": error, "delay_ms": tend - tini}

        if not error:
            # only start the job if the set up was ok
            logger.info("Starting job")
            tini = time.ticks_ms()
            try:
                self.current_job_task = asyncio.create_task(job_coroutine())
            except Exception as exc:
                error = repr(exc)
                logger.error("Started in error: {!r}", exc)
            else:
                error = None
                logger.info("Started ok")
            tend = time.ticks_ms()
            status["started"] = {"error": error, "delay_ms": tend - tini}
        return status

    async def _get_job(self):
        """Return current code."""
        logger.info("Answering current job code")

        # save received code for future restarts
        with open(JOB_FILENAME, "rb") as fh:
            code = fh.read()

        return code

    async def _update_job(self, code):
        """Receive a new job to run."""
        logger.info("Updating current job", len(code))
        switch_status = dict.fromkeys(("stopped", "setup", "started"))

        # save received code for future restarts
        with open(JOB_FILENAME, "wb") as fh:
            fh.write(code)

        switch_status["stopped"] = self._stop_job()
        metrics = self._start_job(code)
        switch_status.update(metrics)

        return json.dumps(switch_status)


system_board = SystemBoard()


async def run():
    logger.info("Start, base mem: {} - datetime: {}", gc.mem_free(), nice_time())
    await system_board.run()


def breath():
    gc.collect()
    data = {"free_mem": gc.mem_free(), "datetime": nice_time()}
    is_connected = system_board.management_client is not None
    logger.debug("Breathing (connected={})... {}", is_connected, data)

    if is_connected:
        system_board.management_client.request("REPORT", json.dumps(data))

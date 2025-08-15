# Copyright 2025 Facundo Batista
# https://github.com/facundobatista/dsaf/

"""Main device code."""

import gc
import json
import os
import time

import machine

from src import logger
from src.button import Button
#from src.comms import ConfigServer
from src.outputs import Led
from src.networkmanager import NetworkManager

# used pins
PIN_FLASH_BUTTON = 0
PIN_POWER_LED = 2
PIN_STATUS_LED = 16


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

    def get(self, key, default=None):
        """Return the value of the key in the storage, default if not present."""
        return self._storage.get(key, default)

    def set(self, key, value):
        """Set and save the key/value pair in the storage."""
        self._storage[key] = value
        with open(self._filepath_temp, "wt") as fh:
            json.dump(self._storage, fh)
        os.rename(self._filepath_temp, self._filepath)


# class ViewsHandler:
#     def __init__(self, storage, action_callback=None):
#         self.storage = storage
#         self.action_callback = action_callback
#
#     def get_operation(self, request):
#         is_mode_automatic = self.storage.get("mode_automatic", False)
#         manual_state = self.storage.get("manual_state", False)
#         auto_freq = self.storage.get("auto_freq")
#         params = {
#             "is_auto_mode_selected": "selected" if is_mode_automatic else "",
#             "is_manual_mode_selected": "" if is_mode_automatic else "selected",
#             "initial_frequency": auto_freq or "Escribe la frecuencia",
#             "initial_button_state": manual_state,
#         }
#         return render_template("actions.html", params)
#
#     def set_operation(self, request):
#         content = request.content
#         if content["mode"] == "manual":
#             is_mode_automatic = False
#             manual_state = content["status"]
#             auto_freq = None
#         else:
#             is_mode_automatic = True
#             manual_state = None
#             try:
#                 auto_freq = float(content["frequency"])
#             except ValueError:
#                 auto_freq = None
#             else:
#                 if auto_freq <= 0:
#                     auto_freq = None
#
#         logger.info(
#             "Action! mode_automatic={}, manual={}, freq={}",
#             is_mode_automatic, manual_state, auto_freq)
#         self.storage.set("mode_automatic", is_mode_automatic)
#         self.storage.set("manual_state", manual_state)
#         self.storage.set("auto_freq", auto_freq)
#         self.action_callback()
#
#     def get_config(self, request):
#         network = self.storage.get("config_network", "")
#         password = self.storage.get("config_pasword", "")
#         params = {
#             "prefill_network": network,
#             "prefill_password": password,
#             "message": "",
#         }
#         return render_template("config.html", params)
#
#     def set_config(self, request):
#         content = request.content
#         network = content["network"]
#         password = content["password"]
#
#         if not is_valid_ssid(network):
#             message = "Nombre de red inválido: hasta 32 letras, números, guión medio o bajo"
#         elif not is_valid_password(password):
#             message = "Password inválida: sólo caracteres ASCII mostrables, entre 8 y 63 de largo"
#         else:
#             logger.info("Config set! network={}, password={}", network, password)
#             self.storage.set("config_network", network)
#             self.storage.set("config_password", password)
#             message = "Configuración cambiada OK"
#
#         params = {
#             "prefill_network": network,
#             "prefill_password": password,
#             "message": message,
#         }
#         return render_template("config.html", params)


class SystemBoard:
    def __init__(self):
        self.storage = Storage("remex.db")

        self.status_led = Led(PIN_STATUS_LED, inverted=True)
        self.power_led = Led(PIN_POWER_LED, inverted=True)
        self.button = Button(PIN_FLASH_BUTTON)

        #self.http_server = None
        #self.network_manager = None

    async def run(self):
        """Start to work the main system."""
        print("==============+X 1")
        # blink leds to indicate we started working
        await self.status_led.blink_once([100, 500, 100, 100, 100, 500])
        print("==============+X 2")

        await self.enter_regular_mode()

    #async def _close_current_servers(self):
    #    """Close/stop current servers/managers."""
    #    logger.debug("Cycling servers! free mem before: {}", gc.mem_free())
    #    if self.network_manager is not None:
    #        logger.info("Stopping previous network manager")
    #        await self.network_manager.stop()
    #        self.network_manager = None
    #    if self.http_server is not None:
    #        logger.info("Stopping previous http server")
    #        await self.http_server.close()
    #        self.http_server = None
    #    gc.collect()
    #    logger.debug("Cycling servers! free mem after:  {}", gc.mem_free())

    async def enter_config_mode(self):
        """Configuration mode.

        - set led to blinking
        - change button to callback to regular mode
        """
        logger.info("Entering Config mode")
        #await self._close_current_servers()
        self.status_led.set(True)
        self.power_led.start_blinking([500, 500])
        self.button.set_interrupt(200, self.enter_regular_mode)

        print("=================== MODE CONFIG")

        # open wifi
        ssid = "Remex-" + machine.unique_id().hex()
        self.network_manager = NetworkManager()
        await self.network_manager.start_ap(ssid, "remex-config")

        # views_handler = ViewsHandler(self.storage)
        # self.http_server = HTTPServer([
        #     ("GET", "/favicon.ico", None),
        #     ("POST", "/config", views_handler.set_config),
        #     ("GET", "/config", views_handler.get_config),
        #     ("GET", "/", views_handler.get_config),
        # ])
        # await self.http_server.start()
        # logger.info("Serving config")

    async def enter_regular_mode(self):
        """Regular operation mode."""
        logger.info("Entering Regular mode")
        #await self._close_current_servers()
        self.status_led.set(False)
        self.power_led.start_blinking([100, 9900])
        self.button.set_interrupt(2500, self.enter_config_mode)

        print("=================== MODE REGULAR")
        # ssid = self.storage.get("config_network")
        # if ssid is None:
        #     logger.info("Warning: no SSID config")
        #     self.green_led.blink([100, 100])
        #     return

        # password = self.storage.get("config_password")
        # logger.info("Starting operation AP")
        # self.green_led.set(True)
        # self.network_manager = NetworkManager()
        # await self.network_manager.start_ap(ssid, password)

        # views_handler = ViewsHandler(self.storage, self.apply_system_state)
        # self.http_server = HTTPServer([
        #     ("GET", "/favicon.ico", None),
        #     ("POST", "/operate", views_handler.set_operation),
        #     ("GET", "/operate", views_handler.get_operation),
        #     ("GET", "/", views_handler.get_operation),
        # ])
        # await self.http_server.start()


system_board = SystemBoard()


async def run():
    logger.set_level(logger.DEBUG)
    logger.info("Start, base mem: {} - time: {}", gc.mem_free(), time.gmtime())
    await system_board.run()


def breath():
    gc.collect()
    logger.debug("Breathing... free mem: {} - time: {}", gc.mem_free(), time.gmtime())

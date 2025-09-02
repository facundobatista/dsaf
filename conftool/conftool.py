# Copyright 2025 Facundo Batista
# https://github.com/facundobatista/dsaf/

"""Configuration tool."""

import argparse
import asyncio
import json
import subprocess
import time

from lib.comms import ProtocolClient, STATUS_OK

DEVICE_AP_CONFIG_PASSWORD = "remex-config"
DEVICE_SSID_PREFIX = "Remex-"


class ErrorSituation(Exception):
    """Used to flag exit and provide a message."""


class ConnectionManager:
    """Context manager to handle the network connections forward and back."""

    def __init__(self, direct):
        self._direct = direct
        self._original_ssid = None

    def __enter__(self):
        if not self._direct:
            self._original_ssid = self._get_current_ssid()
            self._connect_to_device()
        return self

    def __exit__(self, *errinfo):
        if not self._direct:
            self._connect_to_original()

    def _rescan_networks(self):
        """Rescan networks (and wait until it was refreshed, as it's not blocking."""
        # even if we only need the SSID to return, we get other parameters here for better
        # detection of when the scan finished (*something* will change, even if it's only the
        # signal level)
        cmd = ["-f", "ssid,chan,rate,signal", "dev", "wifi"]

        print("[cm] rescan networks")
        all_networks_before = self._nmcli(cmd)
        self._nmcli(["device", "wifi", "rescan"])

        all_networks_now = all_networks_before
        while all_networks_now == all_networks_before:
            print("[cm]    waiting...")
            time.sleep(1)
            all_networks_now = self._nmcli(cmd)

        print("[cm] parsing networks")
        # Example:
        # DIRECT-A2-HP Laser 137fnw:1:65 Mbit/s:94
        # TeleCentro Wifi:7:195 Mbit/s:84
        # dmpresas:7:195 Mbit/s:82
        ssids = [line.split(":")[0] for line in all_networks_now]
        return ssids

    def _connect_to_device(self):
        """Connect to the AP opened by the device."""
        all_ssids = self._rescan_networks()
        device_ssids = [item for item in all_ssids if item.startswith(DEVICE_SSID_PREFIX)]
        try:
            (ssid,) = device_ssids
        except ValueError:
            if device_ssids:
                raise ErrorSituation(f"Too many device APs were found: {device_ssids}")
            else:
                raise ErrorSituation("No device AP was found")

        print("[cm] connect to device AP:", ssid)
        self._nmcli(["device", "wifi", "connect", ssid, "password", DEVICE_AP_CONFIG_PASSWORD])

    def _connect_to_original(self):
        """Connect to the original AP.

        As the machine was already connected to this one before, no need to use a password.
        """
        print("[cm] connect back to original wifi")
        self._nmcli(["connection", "up", "id", self._original_ssid])

    def _nmcli(self, parameters):
        """Run the 'nmcli' tool with the indicated parameters plus some defaults."""
        cmd = ["nmcli", "--terse"] + parameters
        try:
            process = subprocess.run(cmd, check=True, text=True, capture_output=True)
        except FileNotFoundError:
            raise ErrorSituation("Error trying to run 'nmcli'")
        return process.stdout.split("\n")

    def _get_current_ssid(self):
        """Get the SSID of the network the computer is currently connected to."""
        print("[cm] get current AP")
        result = self._nmcli(["-f", "active,ssid", "dev", "wifi"])
        # Example:
        # no:Ruben
        # no:Fibertel WiFi462 2.4
        # yes:MorocoTopo
        # no:Fibertel WiFi148 2.4GHz
        # no:Personal Wifi Zone
        # no:Personal Wifi Zone
        for line in result:
            active, ssid = line.split(":", 1)
            if active == "yes":
                return ssid
        raise ValueError(f"Couldn't get the IP gateway from {result}")

    def _get_connection_gw(self, current_ssid):
        """Find the current connection's GW (waiting for it to be set)."""
        print("[cm]     get connection gateway")
        result = self._nmcli(["-f", "GENERAL.CONNECTION,IP4.GATEWAY", "device", "show"])
        # Example:
        # GENERAL.CONNECTION:Illapa
        # IP4.GATEWAY:192.168.2.1
        #
        # GENERAL.CONNECTION:br-ee836d1e15a0
        # IP4.GATEWAY:
        #
        # GENERAL.CONNECTION:docker0
        # IP4.GATEWAY:
        lines = iter(result)
        while True:
            line = next(lines)
            header, ssid = line.split(":", 1)
            assert header == "GENERAL.CONNECTION"
            line = next(lines)
            header, gw_ip = line.split(":", 1)
            assert header == "IP4.GATEWAY"

            if ssid == current_ssid:
                return gw_ip

            try:
                line = next(lines)
            except StopIteration:
                raise ValueError("Couldn't parse connection gw from {result}")

    def get_device_ip(self):
        """Get the IP to connect in the device."""
        current_ssid = self._get_current_ssid()
        if not current_ssid.startswith("Remex-"):
            raise ErrorSituation("Not connected to a DSAF device.")

        print("[cm] get device's IP")
        while True:
            gw_ip = self._get_connection_gw(current_ssid)
            if gw_ip:
                return gw_ip
            print("[cm]    waiting...")
            time.sleep(1)


async def configure(config_payload, device_ip):
    """Search and return the AP started by the device."""
    client = ProtocolClient("Conftool")
    await client.connect(device_ip, 80)

    print("Asking for health")
    status, content = await client.request("HEALTH")
    assert status == STATUS_OK
    print("Response:", json.loads(content))

    # set timestamp as close as we can of sending the message
    config_payload["current_time_tuple"] = time.gmtime()

    print("Configuring the device")
    status, content = await client.request("CONFIG", json.dumps(config_payload))
    assert status == STATUS_OK

    await client.close()
    print("Done")


async def main(ssid, password, managnode_ip, device_name, direct):
    """Main entry point."""
    config_payload = {
        "name": device_name,
        "wifi_ssid": ssid,
        "wifi_password": password,
        "management_node_ip": managnode_ip,
    }
    with ConnectionManager(direct) as cm:
        await configure(config_payload, cm.get_device_ip())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "ssid", action="store",
        help="The SSID of the WiFi network for the device to connect."
    )
    parser.add_argument(
        "password", action="store",
        help="The password of the WiFi network for the device to connect."
    )
    parser.add_argument(
        "managnode_ip", action="store",
        help="The IP of the Management node."
    )
    parser.add_argument(
        "device_name", action="store",
        help="The name to configure in the device (purely for user's reference)."
    )
    parser.add_argument(
        "--direct", action="store_true",
        help=(
            "Connect directly to the device "
            "(the computer must be already connected to device's AP)"
        )
    )
    args = parser.parse_args()

    try:
        asyncio.run(
            main(args.ssid, args.password, args.managnode_ip, args.device_name, args.direct)
        )
    except ErrorSituation as err:
        print("ERROR!", err)
        exit(1)

# Configuration tool for Remex

New devices with Remex jst installed need to be configured. This is done by this tool.

Normally the sequence is:

- Start the device

- Switch it to config mode (hold down the FLASH button a couple of seconds, see `remex` README for more details)

- Run this tool

- Switch the device to regular mode (simple FLASH press)

At this point the device should be communicating with the Management node. The rest is done there.


## How this tool works

- It will find the device's Access Point (see below some details about this; it may be tricky)

- Will connect to it, start communicating with it

- Ask for device status and general health, and print this info in screen

- Configure the device with the information passed to the tool:
    - network SSID and password of the WiFi the device will connect to
    - the IP of the management node
    - the name of the device (for your reference)

- Close the communication with the device

- Reconnect computer to the WiFi network it was connected before

- Inform all is done

## About the device's Access Point

Finding it may be tricky. There are several details that can complicate the tool in that search; in all cases the tool will produce a proper error message.

The situations are:

- the `nmcli` system tool (which is the one that Conftool uses to operate on the network) may not be installed

- any of the `nmcli` outputs changed substantially and Conftool fails to properly parse it

- there is more than one AP from Remex devices

On any of these failures you can just connect your computer manually to the device's AP, and then run Conftool adding the `--direct` parameter. The device's AP name will look like `Remex-NNN` (where NNN are a bunch of digits), the password is `remex-config`.

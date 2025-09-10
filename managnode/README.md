# Manager node

All this is about the manager node, central to DSAF, that allows human and automated operators to interact with distributed nodes.


## How to run

fades -r requirements.txt main.py


# How it works

It starts to coupled servers: one for interface with users, other to interface with devices.

The server for the devices is exposed in port 7739 (the devices know this), and dialog there is based on a binary protocol.

The server for users is exposed in port 5000, and dialog is based on HTTP REST(ish) endpoints:

- `GET /v1/device/`: List all devices names
- `GET /v1/device/<string:name>/health`: Return the latest health indication from the device
- `GET /v1/device/<string:name>/code`: Return the code that is being executed in the device
- `POST /v1/device/<string:name>/code`: Set code to be executed in the device


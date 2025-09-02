# Copyright 2025 Facundo Batista
# https://github.com/facundobatista/dsaf/

"""Script to test communication between nodes/devices.

Should be used from command line; on one terminal run the server:

    PYTHONPATH=. python3 src/comms.py server <port>

In other terminal run the client

    PYTHONPATH=. python3 src/comms.py client <host> <port> <method> <string>

To play with this, the server supports a method LEN that gives the length of the string, STATS to
count how many different letters it has, and ECHO to test future callback from the server.
"""

import asyncio
import json
import logging
import sys
from collections import Counter

from comms import ProtocolServer, ProtocolClient, STATUS_OK
from comms import logger

logger.set_level(logging.DEBUG)

DEVICE_NAME = "testdevice-123"


async def _client_len(host, port, payload):
    client = ProtocolClient(DEVICE_NAME)
    await client.connect(host, port)
    status, content = await client.request("LEN", payload.encode("utf8"))
    assert status == STATUS_OK
    print("Response:", content)
    await client.close()


async def _client_stats(host, port, payload):
    client = ProtocolClient(DEVICE_NAME)
    await client.connect(host, port)
    status, content = await client.request("STATS", payload.encode("utf8"))
    assert status == STATUS_OK
    print("Response:", json.loads(content))
    await client.close()


async def _client_echo(host, port, payload):

    async def push_callback(content):
        print("The server PUSHED:", repr(content))

    client = ProtocolClient(DEVICE_NAME, callbacks={"ECHO": push_callback})
    await client.connect(host, port)
    status, content = await client.request("ECHO", payload.encode("utf8"))
    assert status == STATUS_OK
    print("Response:", content)
    await client.close()


def _run_client(host, port, method, payload):
    """Run the client when exercising the module from command line."""
    allowed_methods = {
        "LEN": _client_len,
        "STATS": _client_stats,
        "ECHO": _client_echo,
    }
    if method not in allowed_methods:
        print("Error: method must be one of", list(allowed_methods))
        return
    loop = asyncio.new_event_loop()
    func = allowed_methods[method]
    loop.run_until_complete(func(host, port, payload))


def _run_server(port):
    """Run the server when exercising the module from command line."""

    async def _count(text):
        """Count how many of each character the string has."""
        cnt = Counter(text.decode("utf8"))
        return json.dumps(cnt.most_common())

    async def _len(text):
        """Len of the string."""
        return str(len(text))

    async def _echo(text):
        """Senf a future echo of the received text."""
        server.push(DEVICE_NAME, "ECHO", text)

    callbacks = {"LEN": _len, "STATS": _count, "ECHO": _echo}
    server = ProtocolServer(callbacks)

    print("Serving in port", port)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(server.start(port))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    args = sys.argv[1:]
    match args:
        case ["server", port]:
            _run_server(port)
        case ["client", host, port, method, payload]:
            _run_client(host, port, method, payload)
        case _:
            print(__doc__)

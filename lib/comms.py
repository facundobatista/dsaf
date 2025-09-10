# Copyright 2025 Facundo Batista
# https://github.com/facundobatista/dsaf/

"""Communication between nodes/devices.

Main programatic interfaces are ProtocolServer and ProtocolClient, check their docstrings
for instructions on how to use.
"""

import asyncio
import hashlib
import math

from lib import logger

VERSION = b"1"

NULL = b"\x00"

# these numbers, for simplicity to the human, are the same than HTTP status codes
# without the middle 0
STATUS_OK = b"\x20"  # the method succeeded
STATUS_MISS = b"\x44"  # no handler for the method
STATUS_CRASH = b"\x50"  # something else went really bad
STATUS_ERROR = b"\x52"  # the user method failed to execute properly

MISSING = object()


class _Client:
    """Main client representation from the server's POV."""
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

        # hold it cached here
        try:
            self.addr = writer.get_extra_info('peername')
        except KeyError:
            # fails in Micropython
            self.addr = "<unknown-address>"

        # event to block real finalization for the case of callback
        self._should_block_end = None

        # this is set from outside after login / registration
        self.name = None

    def block_finishing(self):
        """The client should block regular finish."""
        self._should_block_end = asyncio.Event()

    def release_finishing(self):
        """The client is clear to finish."""
        if self._should_block_end is not None:
            self._should_block_end.set()

    async def finish(self):
        """Clean up."""
        if self._should_block_end is not None:
            await self._should_block_end.wait()
            self._should_block_end = None

        self.writer.close()
        await self.writer.wait_closed()


async def _raw_recv(reader):
    """Read a message."""
    size_len = int.from_bytes(await reader.readexactly(1))
    payload_len = int.from_bytes(await reader.readexactly(size_len))
    payload = await reader.readexactly(payload_len)

    digest = hashlib.sha1(payload).digest()
    verifier_should = digest[-2:]
    verifier_real = await reader.readexactly(2)
    if verifier_should != verifier_real:
        logger.error(
            "Bad read! size_len={!r} payload_len={!r}; verifiers: should={!r} real={!r}",
            size_len, payload_len, verifier_should, verifier_real)
        payload = b""

    return payload


async def _receive_request(reader):
    """Read input and parse the request message.

    Returns the method and the content.
    """
    payload = await _raw_recv(reader)
    try:
        nullpos = payload.index(NULL)
    except ValueError:
        logger.error("Bad request! Not null found: {!r}", payload)
        return None, None

    return payload[:nullpos], payload[nullpos + 1:]


async def _receive_response(reader):
    """Read input and parse the response message.

    Returns the status code for the response, and the response content itself.
    """
    payload = await _raw_recv(reader)
    return payload[:1], payload[1:]


async def _raw_send(writer, payload):
    """Send a message."""
    payload_len = len(payload)

    # manually calculate `int.bit_length()` (not present in micropython)
    bit_length = math.ceil(math.log(payload_len + 1) / math.log(2))

    size_len = math.ceil(bit_length / 8)  # in bytes
    writer.write(size_len.to_bytes(1))
    writer.write(payload_len.to_bytes(size_len))

    writer.write(payload)

    digest = hashlib.sha1(payload).digest()
    verifier = digest[-2:]
    writer.write(verifier)

    await writer.drain()


async def _send_request(writer, method, content):
    """Build a request message and send it."""
    if isinstance(method, str):
        method = method.encode("ascii")
    if isinstance(content, str):
        content = content.encode("ascii")

    assert NULL not in method
    payload = method + NULL + content
    return await _raw_send(writer, payload)


async def _send_response(writer, statuscode, content):
    """Build a response message and send it."""
    assert len(statuscode) == 1
    payload = statuscode + content
    return await _raw_send(writer, payload)


async def _handle_requests(client, system_callbacks, user_callbacks, clean_callback=None):
    """Handle all requests from one connection."""
    logger.debug("Handler: connection established from {}", client.addr)
    done = False
    try:
        while not done:
            done = await _handle_one_request(client, system_callbacks, user_callbacks)
    except EOFError:
        logger.debug("Handler: connection closed from {}", client.addr)
    except Exception as err:
        logger.error("Handler: Unexpected error: {!r}", err)
        await _send_response(client.writer, STATUS_CRASH, repr(err).encode("utf8"))
    finally:
        # all cleanup is done here
        await client.finish()
        if clean_callback is not None:
            clean_callback(client.name)


async def _handle_one_request(client, system_callbacks, user_callbacks):
    """Handle one request, raw."""
    method_name, content = await _receive_request(client.reader)
    logger.debug("Handler: request method={!r} content_len={}", method_name, len(content))

    # special system callbacks
    cb = system_callbacks.get(method_name)
    if cb is not None:
        response, its_done = await cb(client, content)
        await _send_response(client.writer, STATUS_OK, response)
        return its_done

    # regular user callbacks
    cb = user_callbacks.get(method_name)
    if cb is None:
        logger.error("Handler: handler not found for {!r}", method_name)
        await _send_response(client.writer, STATUS_MISS, method_name)
        return False

    try:
        if content:
            response = await cb(client.name, content)
        else:
            response = await cb(client.name)
        if response is None:
            response = b""
        elif isinstance(response, str):
            response = response.encode("utf8")
    except Exception as err:
        logger.error("Error when calling callback: {!r}", err)
        response = repr(err).encode("utf8")
        status = STATUS_ERROR
    else:
        logger.debug("Handler: response size {:d}", len(response))
        status = STATUS_OK
    await _send_response(client.writer, status, response)
    return False


class ProtocolClient:
    """The communication client.

    Usage:
        client = ProtocolClient(name)
        await client.connect(host, port)
        await client.request("METHOD_X", "whatever payload")

    Optionally, a map of callbacks can be passed to init Client, to receive push requests
    from the server:

        callbacks = {
            "METHOD_X": myhandler.do_x,
        }
        client = ProtocolClient(name, callbacks)
        ...
    """

    def __init__(self, name, callbacks=None):
        self._name = name.encode("utf8")
        self._fward_subconn = None
        self._cback_subconn = None
        if callbacks:
            self._callbacks = {k.encode("ascii"): v for k, v in callbacks.items()}
        else:
            self._callbacks = {}

    async def _listen_callbacks(self):
        """Receive pushed messages and trigger callbacks."""

    async def connect(self, host, port):
        """Connect to a server."""
        logger.debug("P.Client: connecting to {!r}:{}", host, port)

        # connect to the server, and initial handshake to know server capabilities
        reader, writer = await asyncio.open_connection(host=host, port=port)
        self._fward_subconn = _Client(reader, writer)
        await self._handshake()

        # standard login
        await self._login()

        # if needed, indicate we can receive callbacks through a new connection; note that this
        # is the only request from client to server; the rest of usage of this stream
        # will be to receive calls
        if self._callbacks:
            reader, writer = await asyncio.open_connection(host=host, port=port)
            self._cback_subconn = _Client(reader, writer)
            await self._register_callback()
            asyncio.create_task(_handle_requests(self._cback_subconn, {}, self._callbacks))

    async def request(self, method, payload=b""):
        """Send a request to the server."""
        return await self._request(self._fward_subconn, method, payload)

    async def _request(self, client, method, payload):
        """Send a request to the server."""
        await _send_request(client.writer, method, payload)

        # handle the response
        status, content = await _receive_response(client.reader)
        if status != STATUS_OK:
            logger.error("P.Client: bad response! status={[0]:x} content={!r}", status, content)
        return status, content

    async def _handshake(self):
        """Establish first communication with the server."""
        statuscode, content = await self._request(self._fward_subconn, b"HOLA", VERSION)
        if statuscode == STATUS_OK:
            logger.debug("P.Client: handshake OK; server version {!r}", content)
        else:
            logger.error("P.Client: handshake problem; response {[0]:x} {!r}", statuscode, content)

    async def _login(self):
        """Send credentials to the server.

        XXX: we may add some secrets here in the future, stored in the device when configuring.
        """
        statuscode, content = await self._request(self._fward_subconn, "LOGIN", self._name)
        if statuscode == STATUS_OK:
            logger.debug("P.Client: login OK")
        else:
            logger.error("P.Client: login rejected; response {[0]:x} {!r}", statuscode, content)

    async def _register_callback(self):
        """Register a stream to receive callbacks."""
        statuscode, content = await self._request(self._cback_subconn, b"CALLBACK", self._name)
        if statuscode == STATUS_OK:
            logger.debug("P.Client: register callback OK")
        else:
            logger.error("P.Client: register problem; response {[0]:x} {!r}", statuscode, content)

    async def _teardown(self):
        """Finish the communication with the server."""
        statuscode, content = await self._request(self._fward_subconn, b"CHAU", b"")
        if statuscode == STATUS_OK:
            logger.debug("P.Client: teardown OK")
        else:
            logger.error("P.Client: teardown problem; response {[0]:x} {!r}", statuscode, content)

    async def close(self):
        """Close the connection."""
        logger.debug("P.Client: closing main connection")
        await self._teardown()

        self._fward_subconn.writer.close()
        await self._fward_subconn.writer.wait_closed()
        if self._cback_subconn is not None:
            self._cback_subconn.writer.close()
            await self._cback_subconn.writer.wait_closed()

        logger.debug("P.Client: gone")


class ProtocolServer:
    """The communication server.

    Receives a dict with a map from methods names to functions/methods.

    Usage:
        callbacks = {
            "METHOD_X": myhandler.do_x,
        }
        server = Server(callbacks)
        await server.listen(port)
    """

    def __init__(self, callbacks):
        self._user_callbacks = {k.encode("ascii"): v for k, v in callbacks.items()}
        self._system_callbacks = {
            b"HOLA": self._do_handshake,
            b"CHAU": self._do_teardown,
            b"LOGIN": self._do_login,
            b"CALLBACK": self._do_register_callback,
        }
        self._tcp_server = None
        self._callback_clients = {}

    async def _future_push(self, client_name, method, payload):
        """Push a request to the client."""
        client = self._callback_clients.get(client_name, MISSING)
        if client is MISSING:
            logger.error("P.Server: cannot push, client {!r} is missing", client_name)
            return False
        if client is None:
            logger.error("P.Server: cannot push, client {!r} is unidirectional", client_name)
            return False

        await _send_request(client.writer, method, payload)

        # handle the response
        status, content = await _receive_response(client.reader)
        if status != STATUS_OK:
            logger.error("P.Server: bad response! status={[0]:x} content={!r}", status, content)
            return False
        return True

    def push(self, client_name, method, payload):
        """Program a push to the client in the future.

        This function is not async; it just schedules the push for the future and promptly returns.
        """
        asyncio.create_task(self._future_push(client_name, method, payload))

    async def _do_handshake(self, client, payload):
        """Establish first communication with the client.

        Return the version to inform the client and flag in False to continue working.
        """
        logger.debug("P.Server: handshake with client {} version {!r}", client.addr, payload)
        return VERSION, False

    async def _do_teardown(self, client, payload):
        """Finish the communication with the client.

        Return a simple OK and flag in True to break requests loop (as this is the final message).
        """
        logger.debug("P.Server: client {} teardown", client.addr)
        return b"OK", True

    async def _do_login(self, client, payload):
        """Annotate the client.

        XXX: we may validate some secret in the future.

        Return simple OK and flag in False to continue working.
        """
        name = payload.decode("utf8")
        client.name = name
        logger.debug("P.Server: client {} login; name={!r}", client.addr, name)
        self._callback_clients[name] = None
        return b"OK", False

    async def _do_register_callback(self, client, payload):
        """Register the client to receive callbacks.

        Return a simple OK and flag in True to break requests loop (as this connection is
        only to push messages from now on).
        """
        name = payload.decode("utf8")
        client.name = name
        logger.debug("P.Server: client {} register callbacks; name={!r}", client.addr, name)
        self._callback_clients[name] = client
        client.block_finishing()
        return b"OK", True

    def _clean(self, name):
        """Clean internal structures for given client."""
        client = self._callback_clients.get(name)
        if client is not None:
            client.release_finishing()

    async def _handle_requests(self, reader, writer):
        """Handle all requests from one connection."""
        client = _Client(reader, writer)
        await _handle_requests(client, self._system_callbacks, self._user_callbacks, self._clean)

    async def listen(self, port):
        """Start serving."""
        self._tcp_server = await asyncio.start_server(self._handle_requests, "0.0.0.0", port)

    async def stop(self):
        """Stop the HTTP server."""
        if self._tcp_server is None:
            raise RuntimeError("Tried to stop a non existant server")

        self._tcp_server.close()
        await self._tcp_server.wait_closed()
        self._tcp_server = None

        # XXX Facundo 2024-07-25: the first is only available since 3.13, and wait_closed depends
        # of the client be closed (can't force it, needs to wait the client to close on its side)
        #   await self.server.close_clients()
        #   await self.server.wait_closed()

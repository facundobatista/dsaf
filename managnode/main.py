# Copyright 2023-2025 Facundo Batista
# https://github.com/facundobatista/dsaf

"""Management node."""

import asyncio
import datetime
import json

from quart import Quart, request, abort, jsonify
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from db import AsyncSession, init_db, Device
from lib.comms import ProtocolServer
from lib.time_utils import get_gmtime_as_dict

app = Quart(__name__)


@app.route("/v1/device/", methods=["GET"])
async def list_devices():
    """List all devices names."""
    app.logger.info("Listing devices")
    async with AsyncSession() as session:
        stmt = select(Device)
        result = await session.execute(stmt)
        names = [device.name for device in result.scalars().all()]
    return jsonify(names)


@app.route("/v1/device/<string:name>/health", methods=["GET"])
async def health(name):
    """Return the latest health indication from the device."""
    app.logger.info("Getting device health for %r", name)
    async with AsyncSession() as session:
        stmt = select(Device).where(Device.name == name)
        result = await session.execute(stmt)
        try:
            device = result.scalars().one()
        except NoResultFound:
            abort(404)

    return jsonify(device.to_dict())


@app.route("/v1/device/<string:name>/code", methods=["GET"])
async def get_code(name):
    """Return the code that is being executed in the device."""
    print("======= get code from the device", repr(name))
    FIXME
    return "FIXME"


@app.route("/v1/device/<string:name>/code", methods=["POST"])
async def set_code(name):
    """Set code to be executed in the device."""
    print("======= push code to the device", repr(name))
    content = await request.get_data()
    print("======= data", repr(content))
    server = app.config["ProtocolServer"]
    server.push(name, "UPDATE-JOB", content)
    return


async def _save_device_health(client_name, health):
    """Save the device's health to the DB."""
    async with AsyncSession() as session:
        stmt = select(Device).where(Device.name == client_name)
        result = await session.execute(stmt)
        device = result.scalars().one()

        device.last_report_content = health
        device.last_report_date = datetime.datetime.now()
        await session.commit()


async def serve_heartbeat(client_name, data):
    """Receive the heartbeat from devices."""
    FIXME


async def serve_check_in(client_name, data):
    """Handle the check in from devices."""
    print("============= check in", client_name, repr(data))
    async with AsyncSession() as session:
        stmt = select(Device).where(Device.name == client_name)
        result = await session.execute(stmt)
        try:
            result.scalars().one()
        except NoResultFound:
            app.logger.info("Client %r checking in for the first time.", client_name)
            device = Device(name=client_name)
            session.add(device)
            await session.commit()

    health = json.loads(data)
    await _save_device_health(client_name, health)

    # return the current time to keep the device updated
    return json.dumps({"current_time": get_gmtime_as_dict()})


async def start_devices_server():
    """Set up and start the communications Server which handles the devices' connections."""
    app.logger.info("Devices server setup.")

    callbacks = {
        "CHECK-IN": serve_check_in,
        "HEARTBEAT": serve_heartbeat,
    }
    server = ProtocolServer(callbacks)
    await server.listen(7739)
    app.logger.info("Devices server working now.")
    app.config["ProtocolServer"] = server


@app.before_serving
async def startup():
    """Set up on general start."""
    # start DB
    await init_db()

    # start the communication with the devices
    loop = asyncio.get_event_loop()
    loop.create_task(start_devices_server())


@app.after_serving
async def shutdown():
    server = app.config["ProtocolServer"]
    await server.stop()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")

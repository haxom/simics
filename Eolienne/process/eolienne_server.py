#!/usr/bin/env python
# coding=utf8
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "eolienne_server.py"
__version__ = "1.3"

import signal
import sys
import asyncio
from pathlib import Path

from pymodbus.datastore import (ModbusSequentialDataBlock, ModbusServerContext,
                                ModbusSlaveContext)
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server import StartAsyncTcpServer

# Params
listen_int = "0.0.0.0"
listen_port = 502
UNIT = 0x42
BROKEN_FILE = "/tmp/broken"


def signal_handler(sig, frame):
    print("CTRL+C pressed, exiting...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


async def init():
    slaves = {
        UNIT: ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [0]*50),
            co=ModbusSequentialDataBlock(0, [0]*50),
            hr=ModbusSequentialDataBlock(0, [0]*50),
            ir=ModbusSequentialDataBlock(0, [0]*50)
        )
    }
    context = ModbusServerContext(slaves=slaves, single=False)

    # un-broken equipment
    with Path(BROKEN_FILE).open('w') as f:
        f.write("false")

    identity = ModbusDeviceIdentification()
    identity.VendorName = "HAXOM"
    identity.ProductCode = "SIMU-TURBOELEC"
    identity.VendorUrl = "https://github.com/haxom/simics/"
    identity.ProductName = "SIMU-TURBOELEC-EOLIENNE"
    identity.ModelName = "EOLIENNE"
    identity.MajorMinorRevision = "1.3.0"

    await asyncio.gather(
        check_broken_eolienne(context),
        run_server(context, identity, (listen_int, listen_port)),
    )


async def run_server(context, identity, address):
    print(f"Modbus slave launched on {address}")
    await StartAsyncTcpServer(
        context=context,
        identity=identity,
        address=address,
    )


async def check_broken_eolienne(context):
    broken_file = Path(BROKEN_FILE)
    while True:
        if broken_file.is_file() and "true" in broken_file.read_text().lower():
            context[UNIT].setValues(
                fc_as_hex=2,
                address=40,
                values=[True],
            )
        await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(init())
    except Exception as err:
        print("[error] Can't init Modbus server ...")
        print(f"[error] {err}")
        print("[error] exiting...")
        sys.exit(1)

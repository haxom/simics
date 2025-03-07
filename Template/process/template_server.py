#!/usr/bin/env python
# coding=utf8
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "template_server.py"
__version__ = "1.3"

import signal
# System
import sys

from pymodbus.datastore import (ModbusSequentialDataBlock, ModbusServerContext,
                                ModbusSlaveContext)
from pymodbus.device import ModbusDeviceIdentification
# pymodbus
from pymodbus.server import StartTcpServer

# Params
listen_int = "0.0.0.0"
listen_port = 502
UNIT = 0x42


def signal_handler(sig, frame):
    print("CTRL+C pressed, exiting...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def init():
    slaves = {
        UNIT: ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [17]*100),
            co=ModbusSequentialDataBlock(0, [17]*100),
            hr=ModbusSequentialDataBlock(0, [17]*100),
            ir=ModbusSequentialDataBlock(0, [17]*100)
        )
    }
    context = ModbusServerContext(slaves=slaves, single=False)

    identity = ModbusDeviceIdentification()
    identity.VendorName = "HAXOM"
    identity.ProductCode = "SIMU-ICS-TEMPLATE"
    identity.VendorUrl = "https://github.com/haxom/"
    identity.ProductName = "SIMU-ICS"
    identity.ModelName = "TEMPLATE"
    identity.MajorMinorRevision = "1.3.0"

    print(f"Modbus slave launched on {listen_int}:{listen_port}")
    StartTcpServer(
        context=context,
        identity=identity,
        address=(listen_int, listen_port)
    )


if __name__ == "__main__":
    try:
        init()
    except Exception as err:
        print("[error] Can't init Modbus server ...")
        print(f"[error] {err}")
        print("[error] exiting...")
        sys.exit(1)

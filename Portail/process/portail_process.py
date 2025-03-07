#!/usr/bin/env python
# coding=utf8
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "portail_process.py"
__version__ = "1.3"

import signal
# System
import sys
from time import sleep

# pymodbus
from pymodbus.client import ModbusTcpClient

# Options
modbus_server_ip = "127.0.0.1"
modbus_server_port = 502
UNIT = 0x2d

# List of VAR
CAPT1 = 0
CAPT2 = 0
M_UP = 0
M_DOWN = 0
C_UP = 0
C_DOWN = 0
C_STOP = 0
LIGHT1 = 0
LIGHT2 = 0
# End of List of VAR


def signal_handler(sig, frame):
    print("CTRL+C pressed, exiting...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def initdb():
    try:
        client = ModbusTcpClient(
            host=modbus_server_ip,
            port=modbus_server_port
        )
        client.write_register(address=0, value=CAPT1, slave=UNIT)
        client.write_register(address=1, value=CAPT2, slave=UNIT)
        client.write_register(address=2, value=M_UP, slave=UNIT)
        client.write_register(address=3, value=M_DOWN, slave=UNIT)
        client.write_register(address=4, value=C_UP, slave=UNIT)
        client.write_register(address=5, value=C_DOWN, slave=UNIT)
        client.write_register(address=6, value=C_STOP, slave=UNIT)
        client.write_register(address=7, value=LIGHT1, slave=UNIT)
        client.write_register(address=8, value=LIGHT2, slave=UNIT)
    except Exception as err:
        print("[error] Can't init the Modbus coils")
        print(f"[error] {err}")
        print("[error] exiting...")
        sys.exit(1)


def loop_process():
    # Main Process
    err_count = 0

    while True:
        sleep(1)
        try:
            client = ModbusTcpClient(
                host=modbus_server_ip,
                port=modbus_server_port
            )

            # read registers
            CAPT1 = client.read_holding_registers(
                address=0,
                count=1,
                slave=UNIT
            ).registers[0]
            CAPT2 = client.read_holding_registers(
                address=1,
                count=1,
                slave=UNIT
            ).registers[0]
            M_UP = client.read_holding_registers(
                address=2,
                count=1,
                slave=UNIT
            ).registers[0]
            M_DOWN = client.read_holding_registers(
                address=3,
                count=1,
                slave=UNIT
            ).registers[0]
            C_UP = client.read_holding_registers(
                address=4,
                count=1,
                slave=UNIT
            ).registers[0]
            C_DOWN = client.read_holding_registers(
                address=5,
                count=1,
                slave=UNIT
            ).registers[0]
            C_STOP = client.read_holding_registers(
                address=6,
                count=1,
                slave=UNIT
            ).registers[0]
            LIGHT1 = client.read_holding_registers(
                address=7,
                count=1,
                slave=UNIT
            ).registers[0]
            LIGHT2 = client.read_holding_registers(
                address=8,
                count=1,
                slave=UNIT
            ).registers[0]

            # process
            LIGHT1 = CAPT1
            LIGHT2 = CAPT2
            M_UP = (not M_DOWN) and (not CAPT1) and (not C_STOP)\
                and (C_UP or M_UP)
            M_DOWN = (not M_UP) and (CAPT2) and (not C_STOP)\
                and (C_DOWN or M_DOWN)

            # C_* are just buttons
            C_UP = 0
            C_DOWN = 0
            C_STOP = 0

            # CAPT1 & CAPT2 are updated by the PHP script itself

            # save registers
            client.write_register(address=0, value=CAPT1, slave=UNIT)
            client.write_register(address=1, value=CAPT2, slave=UNIT)
            client.write_register(address=2, value=M_UP, slave=UNIT)
            client.write_register(address=3, value=M_DOWN, slave=UNIT)
            client.write_register(address=4, value=C_UP, slave=UNIT)
            client.write_register(address=5, value=C_DOWN, slave=UNIT)
            client.write_register(address=6, value=C_STOP, slave=UNIT)
            client.write_register(address=7, value=LIGHT1, slave=UNIT)
            client.write_register(address=8, value=LIGHT2, slave=UNIT)
        except Exception as err:
            print(f"[error] {err}")
            err_count += 1
            if err_count == 5:
                print("[error] 5 errors happened in the process ! exiting...")
                sys.exit(1)


if __name__ == "__main__":
    sleep(10)
    initdb()
    loop_process()

#!/usr/bin/env python
# coding=utf8
__author__ = 'haxom'
__email__ = 'haxom@haxom.net'
__file__ = 'portail_process.py'
__version__ = '1.2'

import signal
# System
import sys
from time import sleep

# pymodbus
from pymodbus.client import ModbusTcpClient

# Options
modbus_server_ip = '127.0.0.1'
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
    print('CTRL+C pressed, exiting...')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def initdb():
    try:
        client = ModbusTcpClient(modbus_server_ip, modbus_server_port)
        client.write_register(0, CAPT1, slave=UNIT)
        client.write_register(1, CAPT2, slave=UNIT)
        client.write_register(2, M_UP, slave=UNIT)
        client.write_register(3, M_DOWN, slave=UNIT)
        client.write_register(4, C_UP, slave=UNIT)
        client.write_register(5, C_DOWN, slave=UNIT)
        client.write_register(6, C_STOP, slave=UNIT)
        client.write_register(7, LIGHT1, slave=UNIT)
        client.write_register(8, LIGHT2, slave=UNIT)
    except Exception as err:
        print('[error] Can\'t init the Modbus coils')
        print('[error] %s' % err)
        print('[error] exiting...')
        sys.exit(1)


def loop_process():
    # Main Process
    err_count = 0

    while True:
        sleep(1)
        try:
            client = ModbusTcpClient(modbus_server_ip, modbus_server_port)

            # read registers
            CAPT1 = client.read_holding_registers(0, 1, slave=UNIT).registers[0]
            CAPT2 = client.read_holding_registers(1, 1, slave=UNIT).registers[0]
            M_UP = client.read_holding_registers(2, 1, slave=UNIT).registers[0]
            M_DOWN = client.read_holding_registers(3, 1, slave=UNIT).registers[0]
            C_UP = client.read_holding_registers(4, 1, slave=UNIT).registers[0]
            C_DOWN = client.read_holding_registers(5, 1, slave=UNIT).registers[0]
            C_STOP = client.read_holding_registers(6, 1, slave=UNIT).registers[0]
            LIGHT1 = client.read_holding_registers(7, 1, slave=UNIT).registers[0]
            LIGHT2 = client.read_holding_registers(8, 1, slave=UNIT).registers[0]

            # process
            LIGHT1 = CAPT1
            LIGHT2 = CAPT2
            M_UP = (not M_DOWN) and (not CAPT1) and (not C_STOP) and (C_UP or M_UP)
            M_DOWN = (not M_UP) and (CAPT2) and (not C_STOP) and (C_DOWN or M_DOWN)

            # C_* are just buttons
            C_UP = 0
            C_DOWN = 0
            C_STOP = 0

            # CAPT1 & CAPT2 are updated by the PHP script itself

            # save registers
            client.write_register(0, CAPT1, slave=UNIT)
            client.write_register(1, CAPT2, slave=UNIT)
            client.write_register(2, M_UP, slave=UNIT)
            client.write_register(3, M_DOWN, slave=UNIT)
            client.write_register(4, C_UP, slave=UNIT)
            client.write_register(5, C_DOWN, slave=UNIT)
            client.write_register(6, C_STOP, slave=UNIT)
            client.write_register(7, LIGHT1, slave=UNIT)
            client.write_register(8, LIGHT2, slave=UNIT)
        except Exception as err:
            print('[error] %s' % err)
            err_count += 1
            if err_count == 5:
                print('[error] 5 errors happened in the process ! exiting...')
                sys.exit(1)


if __name__ == '__main__':
    sleep(10)
    initdb()
    loop_process()

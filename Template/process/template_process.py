#!/usr/bin/env python
# coding=utf8
__author__ = 'haxom'
__email__ = 'haxom@haxom.net'
__file__ = 'template_process.py'
__version__ = '1.3'

import signal
# System
import sys
# Only use to init Modbus coils with random values
from random import getrandbits as randbits
from time import sleep

# pymodbus
from pymodbus.client import ModbusTcpClient

# Options
modbus_server_ip = '127.0.0.1'
modbus_server_port = 502
UNIT = 0x42


def signal_handler(sig, frame):
    print('CTRL+C pressed, exiting...')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def initdb():
    try:
        client = ModbusTcpClient(host=modbus_server_ip, port=modbus_server_port)
        for registre in range(0, 10):
            client.write_coil(address=registre, value=bool(randbits(1)), slave=UNIT)
            client.write_register(address=registre, value=bool(randbits(1)), slave=UNIT)
    except Exception as err:
        print('[error] Can\'t init the Modbus coils')
        print('[error] %s' % err)
        print('[error] exiting...')
        sys.exit(1)


def loop_process():
    # Main Process (template = flip-flop)
    err_count = 0
    registre_count = 10

    while True:
        sleep(1)
        try:
            client = ModbusTcpClient(host=modbus_server_ip, port=modbus_server_port)

            coils = client.read_coils(address=0, count=registre_count, slave=UNIT)
            coils = coils.bits[:registre_count]
            # flipping booleans from list coils
            coils = [not i for i in coils]
            client.write_coils(address=0, values=coils, slave=UNIT)

            registers = client.read_holding_registers(
                address=0,
                count=registre_count,
                slave=UNIT
            )
            registers = registers.registers[:registre_count]
            registers = [i+1 for i in registers]
            client.write_registers(address=0, values=registers, slave=UNIT)

            updateGPIO(coils, registers)
        except Exception as err:
            print('[error] %s' % err)
            err_count += 1
            if err_count == 5:
                print('[error] 5 errors happened in the process ! exiting...')
                sys.exit(1)


def updateGPIO(coils=[], registers=[]):
    for i in range(len(coils)):
        # do something with GPIO
        print('coils[%d] = %d' % (i, coils[i]))
    print('**********************************************')
    for i in range(len(registers)):
        # do something with GPIO
        print('registers[%d] = %d' % (i, registers[i]))
    print('**********************************************')


if __name__ == '__main__':
    sleep(10)
    initdb()
    loop_process()

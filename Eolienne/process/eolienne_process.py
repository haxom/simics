#!/usr/bin/env python
# coding=utf8
__author__ = 'haxom'
__email__ = 'haxom@haxom.net'
__file__ = 'eolienne_process.py'
__version__ = '1.3'

import signal
# System
import sys
from time import sleep

# pymodbus
from pymodbus.client import ModbusTcpClient

# Options
modbus_server_ip = '127.0.0.1'
modbus_server_port = 502
UNIT = 0x42
WIND_SPEED_FILE = '/tmp/wind.txt'


def signal_handler(sig, frame):
    print('CTRL+C pressed, exiting...')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def initdb():
    try:
        client = ModbusTcpClient(host=modbus_server_ip, port=modbus_server_port)
        # Coils table
        # 0 : eolienne status (manual)
        # 1 : eolienne status (wind speed control, should be between 15km/h and 90km/h)
        #                     (corresponding to 4m/s and 25m/s)
        #
        # Discret Input table
        # 40 : eolienne broken status
        #
        # Holding registers table
        # 0 : wind speed (m/s)
        # 1 : power production (kW)
        # 2-9 : not used
        # 10 : wind min speed (4m/s)
        # 11 : wind max (25 m/s)

        client.write_coils(0, [True, True], slave=UNIT)
        #client.write_coils(25, [False], slave=UNIT)
        client.write_registers(0, [0, 0], slave=UNIT)
        client.write_registers(10, [4, 25], slave=UNIT)
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
            client = ModbusTcpClient(host=modbus_server_ip, port=modbus_server_port)

            coils = client.read_coils(address=0, count=2, slave=UNIT).bits
            coils = coils[:2]
            registers = client.read_holding_registers(address=0, count=2, slave=UNIT).registers
            registers = registers[:2]

            speed_min, speed_max = client.read_holding_registers(address=10, count=2, slave=UNIT).registers
            broken = client.read_discrete_inputs(address=40, count=1, slave=UNIT).bits[0]

            speed = int(open(WIND_SPEED_FILE, 'r').read())
            registers[0] = speed

            # broken
            if broken:
                print('[broken eolienne]')
                registers[1] = 0
                client.write_registers(address=0, values=registers, slave=UNIT)
                continue
            # manual stop
            if not coils[0]:
                print('[stop manually]')
                registers[1] = 0
                client.write_registers(address=0, values=registers, slave=UNIT)
                continue
            # wind speed to slow/quick
            if speed < speed_min or speed > speed_max:
                print('[stop due to the wind speed] (%d m/s)' % registers[0])
                coils[1] = False
                client.write_coil(address=1, value=False, slave=UNIT)
                registers[1] = 0
                client.write_registers(address=0, values=registers, slave=UNIT)
                continue

            powerloss = 0  # 0 % of lost
            # unwanted case : Wind speed < 4 m/s will consume power production (thermic loss)
            if speed < 4:
                powerloss = 25
            if speed < 2:
                powerloss = 50

            # unwanted case : Wind speed > 25 m/s will break the eolienne
            if speed > 25:
                broken = True
                print('[wind breaks the eolienne]')
                # signal Server that eolienne is broken
                with open("/tmp/broken", "w") as f:
                    f.write("true")
                registers[1] = 0
                client.write_registers(address=0, values=registers, slave=UNIT)
                continue

            # otherwise, running
            # [production] P = 0.29 * D^2 * v^3
            #   P = power (W)
            #   D = rotor diameter = 23m
            #   v = wind speed (m/s)
            coils[1] = True

            power = (0.29 * pow(23, 2) * pow(registers[0], 3))/1000
            if powerloss != 0:
                power = power*(1-powerloss/100)
            registers[1] = int(power)

            client.write_coils(address=0, values=coils, slave=UNIT)
            client.write_registers(address=0, values=registers, slave=UNIT)

        except Exception as err:
            print(f'[ERROR] {err}')
            err_count += 1
            if err_count == 5:
                print('[CRITICAL] Too much errors occured during the process !')
                print('[CRITICAL] Exiting.')
                sys.exit(1)


if __name__ == '__main__':
    sleep(10)
    initdb()
    loop_process()

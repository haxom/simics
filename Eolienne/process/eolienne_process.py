#!/usr/bin/env python
# coding=utf8
__author__ = 'haxom'
__email__ = 'haxom@haxom.net'
__file__ = 'eolienne_process.py'
__version__ = '1.2'

import signal
# System
import sys
# random to simulate wind speed
from random import getrandbits as randbits
from random import randint
from time import sleep

# pymodbus
from pymodbus.client import ModbusTcpClient

# Options
modbus_server_ip = '127.0.0.1'
modbus_server_port = 502
UNIT = 0x42
speed = 10  # initial wind speed


def signal_handler(sig, frame):
    print('CTRL+C pressed, exiting...')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def initdb():
    try:
        client = ModbusTcpClient(modbus_server_ip, modbus_server_port)
        # Coils table
        # 0 : eolienne status (manual)
        # 1 : eolienne status (wind speed control, should be between 15km/h and 90km/h)
        #                     (corresponding to 4m/s and 25m/s)
        # 25 : eolienne broken status
        #
        # Holding registers table
        # 0 : wind speed (m/s)
        # 1 : power production (kW)
        # 2-9 : not used
        # 10 : wind min speed (4m/s)
        # 11 : wind max (25 m/s)

        client.write_coils(0, [True, True], slave=UNIT)
        client.write_coils(25, [False], slave=UNIT)
        client.write_registers(0, [speed, 0], slave=UNIT)
        client.write_registers(10, [4, 25], slave=UNIT)
    except Exception as err:
        print('[error] Can\'t init the Modbus coils')
        print('[error] %s' % err)
        print('[error] exiting...')
        sys.exit(1)


def loop_process():
    global speed
    # Main Process
    err_count = 0
    gust_state = 0  # 0 = no / 1 = begin / 2 = in progress / 3 = last
    gust_cmp = 0

    while True:
        sleep(1)
        # try gust
        if gust_state == 3:
            gust_state = 0
        if gust_state == 1 or gust_state == 2:
            gust_state = 2
            gust_cmp -= 1
            if gust_cmp == 0:
                gust_state = 3

        if randint(0, 20) == 10 and gust_state == 0:
            gust_state = 1
            gust_cmp += 5

        try:
            client = ModbusTcpClient(modbus_server_ip, modbus_server_port)

            coils = client.read_coils(0, count=2, slave=UNIT).bits
            coils = coils[:2]
            registers = client.read_holding_registers(0, count=2, slave=UNIT).registers
            registers = registers[:2]

            speed_min, speed_max = client.read_holding_registers(10, 2, slave=UNIT).registers
            broken = client.read_coils(25, count=1, slave=UNIT).bits[0]

            # update wind speed
            global speed
            if randbits(1):
                speed += 1
            else:
                speed -= 1
            if gust_state == 1:
                print('**new gust**')
                speed += 10
            if gust_state == 3:
                print('**eo gust**')
                speed -= 10
            if speed < 0:
                speed = 0
            if speed > 30:
                speed = 30
            registers[0] = speed

            # broken
            if broken:
                print('[broken eolienne]')
                registers[1] = 0
                client.write_registers(0, registers, slave=UNIT)
                continue
            # manual stop
            if not coils[0]:
                print('[stop manually]')
                registers[1] = 0
                client.write_registers(0, registers, slave=UNIT)
                continue
            # wind speed to slow/quick
            if speed < speed_min or speed > speed_max:
                print('[stop due to the wind speed] (%d m/s)' % registers[0])
                coils[1] = False
                client.write_coil(1, False, slave=UNIT)
                registers[1] = 0
                client.write_registers(0, registers, slave=UNIT)
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
                client.write_coil(25, True, slave=UNIT)
                registers[1] = 0
                client.write_registers(0, registers, slave=UNIT)
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

            client.write_coils(0, coils, slave=UNIT)
            client.write_registers(0, registers, slave=UNIT)

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

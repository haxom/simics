#!/usr/bin/env python
#coding=utf8
__author__      = 'haxom'
__email__       = 'haxom@haxom.net'
__file__        = 'eolienne_process.py'
__version__     = '1.0'

# Options
modbus_server_ip = '127.0.0.1'
modbus_server_port = 5002
GPIO = False
UNIT=0x42
speed = 10 # initial wind speed 

# pymodbus
from pymodbus.client.sync import ModbusTcpClient

# System
import sys
import signal
from time import sleep

# random to simulate wind speed
from random import randint
from random import getrandbits as randbits

# GPIO
if GPIO:
    import RPi.GPIO as IO
    IO.setwarnings(False)
GPIO_MANUAL_RED = 16
GPIO_MANUAL_GREEN = 19
GPIO_AUTO_RED = 20
GPIO_AUTO_GREEN = 26
GPIO_GUST = 6
GPIO_MOTOR = 13


def signal_handler(sig, frame):
    print 'CTRL+C pressed, exiting...'
    if GPIO:
        IO.cleanup()        
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
        
        client.write_coils(0, [True, True], unit=UNIT)
        client.write_coils(25, [False], unit=UNIT)
        client.write_registers(0, [speed, 0], unit=UNIT)
        client.write_registers(10, [4, 25], unit=UNIT)
    except Exception as err:
        print '[error] Can\'t init the Modbus coils'
        print '[error] %s' % err
        print '[error] exiting...'
        sys.exit(1)

def initGPIO():
    if GPIO:
        IO.setmode(IO.BCM)
        IO.setup(GPIO_MANUAL_RED, IO.OUT)
        IO.setup(GPIO_MANUAL_GREEN, IO.OUT)
        IO.setup(GPIO_AUTO_RED, IO.OUT)
        IO.setup(GPIO_AUTO_GREEN, IO.OUT)
        IO.setup(GPIO_GUST, IO.OUT)
        IO.setup(GPIO_MOTOR, IO.OUT)

def loop_process():
    global speed
    # Main Process
    err_count = 0
    coils_count = 20
    gust_state = 0 # 0 = no / 1 = begin / 2 = in progress / 3 = last
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

            coils = client.read_coils(0, count=2, unit=UNIT).bits
            coils = coils[:2]
            registers = client.read_holding_registers(0, count=2, unit=UNIT).registers
            registers = registers[:2]

            speed_min, speed_max = client.read_holding_registers(10, 2, unit=UNIT).registers
            broken = client.read_coils(25, count=1, unit=UNIT).bits[0]

            # update wind speed
            ## speed = registers[0]
            global speed
            if randbits(1):
                speed += 1
            else:
                speed -= 1
            if gust_state == 1:
                print '**new gust**'
                speed += 10
            if gust_state == 3:
                print '**eo gust**'
                speed -= 10
            if speed < 0:
                speed = 0
            if speed > 30:
                speed = 30
            registers[0] = speed

            # broken
            if broken:
                print '[broken eolienne]'
                registers[1] = 0
                client.write_registers(0, registers, unit=UNIT)
                updateGPIO(coils, gust_state)
                continue
            # manual stop
            if not coils[0]:
                print '[stop manually]'
                registers[1] = 0
                client.write_registers(0, registers, unit=UNIT)
                updateGPIO(coils, gust_state)
                continue
            # wind speed to slow/quick
            if speed < speed_min or speed > speed_max:
                print '[stop due to the wind speed] (%d m/s)' % registers[0]
                coils[1] = False
                client.write_coil(1, False, unit=UNIT)
                registers[1] = 0
                client.write_registers(0, registers, unit=UNIT)
                updateGPIO(coils, gust_state)
                continue

            powerloss = 0 # 0 % of lost
            # unwanted case : Wind speed < 4 m/s will consume power production (thermic loss)
            if speed < 4:
                powerloss = 25 
            if speed < 2:
                powerloss = 50

            # unwanted case : Wind speed > 25 m/s will break the eolienne
            if speed > 25:
                broken = True
                print '[wind breaks the eolienne]'
                client.write_coil(25, True, unit=UNIT)
                registers[1] = 0
                client.write_regiser(0, registers, unit=UNIT)
                continue

            # otherwise, running
            # [production] P = 0.29 * D^2 * v^3
            #   P = power (W)
            #   D = rotor diameter = 24m
            #   v = wind speed (m/s)
            coils[1] = True

            power = (0.29 * pow(24, 2) * pow(registers[0], 3))/1000
            if powerloss != 0:
                power = int(power*(1-powerloss/100))
            registers[1] = power

            print 'producting %d kW (%d m/s)' % (registers[1], registers[0])

            client.write_coils(0, coils, unit=UNIT)
            client.write_registers(0, registers, unit=UNIT)

            if GPIO:
                updateGPIO(coils, gust_state)
        except Exception as err:
            print '[error] %s' % err
            err_count += 1
            if err_count == 5:
                print '[error] 5 errors happened in the process ! exiting...'
                sys.exit(1)

def updateGPIO(coils=[], gust_state=0):
    if GPIO:
        # coils[0] => manual START/STOP
        # coils[1] => auto   START/STOP
        if gust_state != 0:
            IO.output(GPIO_GUST, 1)
        else:
            IO.output(GPIO_GUST, 0)
        if coils[0]:
            IO.output(GPIO_MANUAL_GREEN, 1)
            IO.output(GPIO_MANUAL_RED, 0)
        else:
            IO.output(GPIO_MANUAL_GREEN, 0)
            IO.output(GPIO_MANUAL_RED, 1)
        if coils[1]:
            IO.output(GPIO_AUTO_GREEN, 1)
            IO.output(GPIO_AUTO_RED, 0)
        else:
            IO.output(GPIO_AUTO_GREEN, 0)
            IO.output(GPIO_AUTO_RED, 1)

        if coils[0] and coils[1]:
            IO.output(GPIO_MOTOR, 1)
        else:
            IO.output(GPIO_MOTOR, 0)
    
if __name__ == '__main__':
    sleep(10)
    initdb()
    initGPIO()
    loop_process()

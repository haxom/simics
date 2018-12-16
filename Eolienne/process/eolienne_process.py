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
    import RPi.GPIO as GPIO


def signal_handler(sig, frame):
    print 'CTRL+C pressed, exiting...'
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

def initdb():
    try:
        client = ModbusTcpClient(modbus_server_ip, modbus_server_port)
        # Coils table
        # 0 : eolienne status (manual)
        # 1 : eolienne status (wind speed control, should be between 15km/h and 90km/h)
        #                     (corresponding to 4m/s and 25m/s)
        #
        # Holding registers table
        # 10 : wind speed (m/s)
        # 11 : power production (kW)
        
        client.write_coils(0, [True, True], unit=UNIT)
        client.write_registers(0, [speed, 0], unit=UNIT)
    except Exception as err:
        print '[error] Can\'t init the Modbus coils'
        print '[error] %s' % err
        print '[error] exiting...'
        sys.exit(1)

def initGPIO():
    if GPIO:
        GPIO.setmode(GPIO.BCM)
        # GPIO 2 to 21 are usable as I/O
        for i in range(2, 22):
            GPIO.setup(i, GPIO.OUT)

def loop_process():
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

            # manual stop
            if not coils[0]:
                print '[stop manually]'
                registers[1] = 0
                client.write_registers(0, registers, unit=UNIT)
                continue
            # wind speed to slow/quick
            if registers[0] < 4 or registers[0] > 25:
                print '[stop due to the wind speed] (%d m/s)' % registers[0]
                coils[1] = False
                client.write_coil(1, False, unit=UNIT)
                continue
            else:
                coils[1] = True

            # otherwise, running
            # [production] P = 0.29 * D^2 * v^3
            #   P = power (W)
            #   D = rotor diameter = 24m
            #   v = wind speed (m/s)

            registers[1] = (0.29 * pow(24, 2) * pow(registers[0], 3))/1000
            print 'producting %d kW (%d m/s)' % (registers[1], registers[0])

            client.write_coils(0, coils, unit=UNIT)
            client.write_registers(0, registers, unit=UNIT)

            #updateGPIO(coils, registers)
        except Exception as err:
            print '[error] %s' % err
            err_count += 1
            if err_count == 5:
                print '[error] 5 errors happened in the process ! exiting...'
                sys.exit(1)

def updateGPIO(coils=[], registers=[]):
    if GPIO:
        # coils 0 -> 19 aligned with GPIO pins 2 -> 21
        for i in range(len(coils)):
            GPIO.output(i+2, coils[i])
    else:
        for i in range(len(coils)):
            # do something with GPIO
            print 'coils[%d] = %d' % (i, coils[i])
        print '**********************************************'
        for i in range(len(registers)):
            # do something with GPIO
            print 'registers[%d] = %d' % (i, registers[i])
        print '**********************************************'

    
if __name__ == '__main__':
    sleep(10)
    initdb()
    initGPIO()
    loop_process()

#!/usr/bin/env python
#coding=utf8
__author__      = 'haxom'
__email__       = 'haxom@haxom.net'
__file__        = 'template_process.py'
__version__     = '1.0'

# Options
modbus_server_ip = '127.0.0.1'
modbus_server_port = 5002
GPIO = False
UNIT = 0x42

# pymodbus
from pymodbus.client.sync import ModbusTcpClient

# System
import sys
import signal
from time import sleep

# GPIO
if GPIO:
    import RPi.GPIO as GPIO

# Only use to init Modbus coils with random values
from random import getrandbits as randbits


def signal_handler(sig, frame):
    print 'CTRL+C pressed, exiting...'
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

def initdb():
    try:
        client = ModbusTcpClient(modbus_server_ip, modbus_server_port)
        for registre in range(0,10):
            client.write_coil(registre, bool(randbits(1)), unit=UNIT)
            client.write_register(registre, bool(randbits(1)), unit=UNIT)
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
    # Main Process (template = flip-flop)
    err_count = 0
    registre_count = 10


    while True:
        sleep(1)
        try:
            client = ModbusTcpClient(modbus_server_ip, modbus_server_port)

            coils = client.read_coils(0, count=registre_count, unit=UNIT)
            coils = coils.bits[:registre_count]
            # flipping booleans from list coils
            coils = [not i for i in coils]
            client.write_coils(0, coils)

            registers = client.read_holding_registers(0, count=registre_count, unit=UNIT)
            registers = registers.registers[:registre_count]
            registers = [i+1 for i in registers]
            client.write_registers(0, registers, unit=UNIT)

            updateGPIO(coils, registers)
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

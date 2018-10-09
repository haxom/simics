#!/usr/bin/env python
#coding=utf8
__author__      = 'haxom'
__email__       = 'haxom@haxom.net'
__file__        = 'template.py'
__version__     = '0.1a'

# Options
modbus_server_ip = '127.0.0.1'
modbus_server_port = 5002
GPIO = False

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
        for registre in range(0,20):
            client.write_coil(registre, bool(randbits(1)))
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
    coils_count = 20

    while True:
        sleep(1)
        try:
            client = ModbusTcpClient(modbus_server_ip, modbus_server_port)

            coils = client.read_coils(0, count=coils_count)
            coils = coils.bits[:coils_count]
            # flipping booleans from list coils
            coils = [not i for i in coils]
            client.write_coils(0, coils)
            updateGPIO(coils)
        except Exception as err:
            print '[error] %s' % err
            err_count += 1
            if err_count == 5:
                print '[error] 5 errors happened in the process ! exiting...'
                sys.exit(1)

def updateGPIO(coils=[]):
    if GPIO:
        # coils 0 -> 19 aligned with GPIO pins 2 -> 21
        for i in range(len(coils)):
            GPIO.output(i+2, coils[i])
    else:
        for i in range(len(coils)):
            # do something with GPIO
            print 'coils[%d] = %d' % (i, coils[i])
        print '**********************************************'
    
if __name__ == '__main__':
    initdb()
    initGPIO()
    loop_process()

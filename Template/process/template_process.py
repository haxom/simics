#!/usr/bin/env python
#coding=utf8
__author__      = 'haxom'
__email__       = 'haxom@haxom.net'
__file__        = 'template.py'
__version__     = '0.1a'

# pymodbus
from pymodbus.client.sync import ModbusTcpClient

# System
import sys
import signal
from time import sleep

# Params
modbus_server_ip = '127.0.0.1'
modbus_server_port = 5002


def signal_handler(sig, frame):
    print 'CTRL+C pressed, exiting...'
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

def initdb():
    client = ModbusTcpClient(modbus_server_ip, modbus_server_port)
    for registre in range(1,21):
        client.write_coil(registre, False)

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
    for i in range(len(coils)):
        # do something with GPIO
        print 'coils[%d] = %d' % (i, coils[i])
    print '**********************************************'

if __name__ == '__main__':
    initdb()
    loop_process()

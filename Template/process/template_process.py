#!/usr/bin/env python
#coding=utf8
__author__      = 'haxom'
__email__       = 'haxom@haxom.net'
__file__        = 'template.py'
__version__     = '0.1a'

# pymodbus
from pymodbus.client.sync import ModbusTcpClient

# Threading
from threading import Thread
from time import sleep

# System
import sys
import signal

def signal_handler(sig, frame):
    print 'CTRL+C pressed, exiting...'
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

def initdb():
    client = ModbusTcpClient('127.0.0.1', 5002)
    #client = ModbusTcpClient('127.0.0.1', 502)
    for registre in range(1,21):
        client.write_coil(registre, False)

def updatedb():
    # Main Process (template = flip-flop)
    while True:
        sleep(0.5)
        try:
            client = ModbusTcpClient('127.0.0.1', 5002)
            #client = ModbusTcpClient('127.0.0.1', 502)

            coils = client.read_coils(1,21)
            for i in range(20):
                if coils[i]:
                    client.write_coil(i+1, False)
                else:
                    client.write_coil(i+1, True)
        except Exception as err:
            print '[error] %s' % err


if __name__ == '__main__':
    th = Thread(target=updatedb)
    th.start()
    th.join()

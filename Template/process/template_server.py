#!/usr/bin/env python
#coding=utf8
__author__      = 'haxom'
__email__       = 'haxom@haxom.net'
__file__        = 'template_server.py'
__version__     = '0.1a'

# pymodbus
from pymodbus.server.sync import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

from pymodbus.client.sync import ModbusTcpClient

# Rasp GPIO

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


def updateGPIO():
    while True:
        sleep(0.5)
        try:
            client = ModbusTcpClient('127.0.0.1', 5002)
            #client = ModbusTcpClient('127.0.0.1', 502)
            coils = client.read_coils(1,20)
            for i in range(20):
                print 'Coil %d = %d' % (i, coils.bits[i])
        except Exception as err:
            print '[error] %s' % err

def init():
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [17]*100),
        co=ModbusSequentialDataBlock(0, [17]*100),
        hr=ModbusSequentialDataBlock(0, [17]*100),
        ir=ModbusSequentialDataBlock(0, [17]*100)
    )
    context = ModbusServerContext(slaves=store, single=True)

    identity = ModbusDeviceIdentification()
    identity.VendorName = ''
    identity.ProductCode = ''
    identity.VendorUrl = ''
    identity.ProductName = ''
    identity.ModelName = ''
    identity.MajorMinorRevision = ''

    StartTcpServer(context, identity=identity, address=('localhost', 5002))
    #StartTcpServer(context, identity=identity, address=('localhost', 502)

if __name__ == '__main__':
    th = Thread(target=updateGPIO)
    th.start()
    init()

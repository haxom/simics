#!/usr/bin/env python
#coding=utf8
__author__      = 'haxom'
__email__       = 'haxom@haxom.net'
__file__        = 'eolienne_server.py'
__version__     = '1.0'

# pymodbus
from pymodbus.server.sync import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

from pymodbus.client.sync import ModbusTcpClient

# System
import sys
import signal

# Params
listen_int = '127.0.0.1'
listen_port = 5002

def signal_handler(sig, frame):
    print 'CTRL+C pressed, exiting...'
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)


def init():
    slaves = {
        0x42: ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [0]*10),
            co=ModbusSequentialDataBlock(0, [0]*10),
            hr=ModbusSequentialDataBlock(0, [0]*10),
            ir=ModbusSequentialDataBlock(0, [0]*10)
        )
    }
    context = ModbusServerContext(slaves=slaves, single=False)

    identity = ModbusDeviceIdentification()
    identity.VendorName = ''
    identity.ProductCode = ''
    identity.VendorUrl = ''
    identity.ProductName = ''
    identity.ModelName = ''
    identity.MajorMinorRevision = ''

    print 'Launching Modbus server, listening on %s:%d' % (listen_int, listen_port)
    StartTcpServer(context, identity=identity, address=(listen_int, listen_port))

if __name__ == '__main__':
    try:
        init()
    except Exception as err:
        print '[error] Can\'t init Modbus server ...'
        print '[error] %s' % err
        print '[error] exiting...'
        sys.exit(1)

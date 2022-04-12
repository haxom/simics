#!/bin/env python3
import sys
import os
sys.path.insert(0, "..")
import time
from pymodbus.client.sync import ModbusTcpClient
from opcua import ua, Server


UNIT=0x42


def eol_connect(ips):
    conns = dict()
    for ip in ips:
        conns[ip] = ModbusTcpClient(ip, 502)
    return conns


def displayParc(parc):
    print(f'* {parc.get_browse_name().Name} ({parc.get_children()[0].get_value()} kW)')
    for eol in parc.get_children():
        if 'eolienne' not in eol.get_browse_name().Name:
            continue
        print(f'** {eol.get_browse_name().Name}')
        for var in eol.get_variables():
            if var.get_display_name().Text == 'status_manual':
                print(f'\tStatus manual : {var.get_value()}')
            if var.get_display_name().Text == 'status_auto':
                print(f'\tStatus auto : {var.get_value()}')
            if var.get_display_name().Text == 'wind_speed':
                print(f'\tWind speed : {var.get_value()} m/s')
            if var.get_display_name().Text == 'power':
                print(f'\tPower : {var.get_value()} kW')
    print('')

if __name__ == "__main__":
    # Check if IPs of turbines are provided
    ips = os.environ['EOL_IP'].split(';')
    if ips[0] == '':
        print("No turbine's IP addresses provided !")
        sys.exit(1)


    # setup OPC-UA server
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/serveropcua/server/")
    server.set_server_name("TURBOElec OPC Supervisor")
    # setup namespace (not used)
    uri = "https://github.com/haxom/simics/"
    idx = server.register_namespace(uri)

    # setup object node
    objects = server.get_objects_node()
    parc = server.nodes.objects.add_object(idx, "Parc éolien")
    parc.add_variable(idx, "power", 0)

    # populating our address space
    for ip in ips:
        eol = parc.add_object(idx, f'eolienne_{ip}')
        status_manual = eol.add_variable(idx, "status_manual", 1)
        status_auto = eol.add_variable(idx, "status_auto", 1)
        wind_speed = eol.add_variable(idx, "wind_speed", 0)
        power = eol.add_variable(idx, "power", 0)

        # status_manual.set_writable()

    # starting!
    server.start()

    # connection to the PLC via Modbus
    clients = eol_connect(ips)
    
    try:
        while True:
            time.sleep(1)
            power = 0
            for ip in ips:
                coils = clients[ip].read_coils(0, count=2, unit=UNIT).bits
                registers = clients[ip].read_holding_registers(0, count=2, unit=UNIT).registers
    
                for eol in parc.get_children():
                    if 'eolienne' not in eol.get_browse_name().Name:
                        continue
                    if ip not in eol.get_browse_name().Name:
                        continue
                    for var in eol.get_variables():
                        if var.get_display_name().Text == 'status_manual':
                            var.set_value(coils[0])
                        elif var.get_display_name().Text == 'status_auto':
                            var.set_value(coils[1])
                        elif var.get_display_name().Text == 'wind_speed':
                            var.set_value(registers[0])
                        elif var.get_display_name().Text == 'power':
                            var.set_value(registers[1])
                            power = power + registers[1]
                        else:
                            print(f'Error with var : {var.get_display_name()()}')

            parc.get_variables()[0].set_value(power)
            displayParc(parc)

    finally:
        #close connection, remove subcsriptions, etc
        server.stop()

#!/usr/bin/env python
# coding=utf8
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "eolienne_process.py"
__version__ = "1.5"

import signal
import sys
from time import sleep
from pymodbus.client import ModbusTcpClient

# Options
modbus_server_ip = "127.0.0.1"
modbus_server_port = 502
UNIT = 0x42
RPM_MAX = 43


def signal_handler(sig, frame):
    print("CTRL+C pressed, exiting...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def initdb():
    try:
        client = ModbusTcpClient(
            host=modbus_server_ip,
            port=modbus_server_port
        )
        # Coils table
        # 0 : eolienne manual status
        # 1 : eolienne automatic status (wind speed control
        #   - wind speed control - should be between 4m/s and 25m/s
        #   - (not implemented yet) temperature control - should be < 80°C
        #   - (not implemented yet) birds detection - should be no birds
        #   - rotor speed control - should be < RPM max
        #
        # Discret Input table
        # 40 : eolienne broken status
        #
        # Holding registers table
        # 0 : pitch angle (°)
        # 1 : wind speed (m/s)
        # 2 : rotor speed (rpm)
        # 3 : yaw angle (°)
        # 4 : temperature (°C) - not implemented yet
        # 5-9 : reserved
        # 10 : mechanical power (kW)
        # 11 : electrical power (kW)
        # 12-19 : reserved
        # 20 : wind min speed (4m/s)
        # 21 : wind max (25 m/s)
        # 22 : max_rotor_speed (RPM_MAX)
        # 23-24  reserved
        # 25 : automatic stop reason
        #   - 0 : no reason
        #   - 1 : wind speed
        #   - 2 : rotor speed

        client.write_coils(0, [True, True], device_id=UNIT)
        client.write_registers(20, [4, 25, RPM_MAX, 0, 0, 0], device_id=UNIT)
    except Exception as err:
        print("[error] Can't init the Modbus coils")
        print(f"[error] {err}")
        print("[error] exiting...")
        sys.exit(1)


def loop_process():
    # Main Process
    err_count = 0
    while True:
        sleep(1)

        try:
            client = ModbusTcpClient(
                host=modbus_server_ip,
                port=modbus_server_port
            )

            status_manual, status_auto = client.read_coils(
                address=0,
                count=2,
                device_id=UNIT,
            ).bits[:2]

            speed_min, speed_max, max_rotor_speed = client.read_holding_registers(
                address=20,
                count=3,
                device_id=UNIT
            ).registers

            pitch, speed, rotor_speed, yaw = client.read_holding_registers(
                address=0,
                count=4,
                device_id=UNIT
            ).registers

            broken = client.read_discrete_inputs(
                address=40,
                count=1,
                device_id=UNIT
            ).bits[0]

            # broken
            if broken:
                print("[broken eolienne]")
                # set all values to 0
                client.write_coils(address=0, values=[False]*50, device_id=UNIT)
                client.write_registers(address=0, values=[0]*50, device_id=UNIT)
                continue
            # manual stop
            if not status_manual:
                print("[stop manually]")
                client.write_registers(address=25, values=[0], device_id=UNIT)
                continue
            # wind speed too slow/quick
            if speed/100 < speed_min or speed/100 > speed_max:
                print(f"[stop due to the wind speed] ({speed/100} m/s)")
                client.write_coil(address=1, value=False, device_id=UNIT)
                client.write_registers(address=25, values=[1], device_id=UNIT)
                continue
            # rotor speed too high
            if rotor_speed > max_rotor_speed:
                print(f"[stop due to rotor RPM to high] ({rotor_speed} rpm (max {max_rotor_speed} rpm))")
                client.write_coil(address=1, value=False, device_id=UNIT)
                client.write_registers(address=25, values=[2], device_id=UNIT)
                continue

            # otherwise, running
            client.write_coil(address=1, value=True, device_id=UNIT)
            client.write_registers(address=25, values=[0], device_id=UNIT)

        except Exception as err:
            print(f"[ERROR] {err}")
            err_count += 1
            if err_count == 5:
                print("[CRITICAL] Too much errors occured during the process!")
                print("[CRITICAL] Exiting.")
                sys.exit(1)


if __name__ == "__main__":
    sleep(10)
    initdb()
    loop_process()

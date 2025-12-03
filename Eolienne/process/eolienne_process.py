#!/usr/bin/env python
# coding=utf8
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "eolienne_process.py"
__version__ = "1.3"

import math
from random import randint
import signal
# System
import sys
from time import sleep

# pymodbus
from pymodbus.client import ModbusTcpClient

# Options
modbus_server_ip = "127.0.0.1"
modbus_server_port = 502
UNIT = 0x42
WIND_SPEED_FILE = "/tmp/wind.txt"
BROKEN_FILE = "/tmp/broken"

# --- Fixed turbine parameters ---
# Some values from Vestas V27
# (https://en.wind-turbine-models.com/turbines/274-vestas-v27)
R = 27/2                    # rotor radius (m)
A = math.pi * R**2          # swept area (m²)
TIP_SPEED_MAX = 61          # m/s
SURVIVAL_WIND_SPEED = 56    # m/s
RPM_MAX = (60 / (2 * math.pi)) * (TIP_SPEED_MAX / R)
RPM_MAX = int(RPM_MAX)      # max rotor speed (rpm)
P_RATED = 225.0             # kW
ETA = 0.95                  # generator + converter efficiency
RHO = 1.225                 # air density (kg/m³)


def signal_handler(sig, frame):
    print("CTRL+C pressed, exiting...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


# --- Lambda_opt as function of pitch (deg) ---
def lambda_opt(beta_deg):
    return 7.5 - 0.12*beta_deg


# --- Cp approximation (drops as pitch increases) --
def cp(lambda_val, beta_deg):
    cp0 = 0.42                            # max Cp
    loss = 0.005 * beta_deg               # degrade with pitch
    return max(0.0, cp0 - loss)


# --- Rotor speed in RPM ---
def rpm(V_ms, yaw_deg, beta_deg, rpm_max):
    Veff = V_ms * math.cos(math.radians(yaw_deg))
    if Veff <= 0:
        return 0.0
    lam = lambda_opt(beta_deg)
    rpm_val = (60 / (2 * math.pi)) * (lam * Veff / R)
    return int(min(rpm_val/2, rpm_max))


# --- Mechanical power (from aerodynamics) ---
def mechanical_power(V_ms, yaw_deg, beta_deg):
    Veff = V_ms * math.cos(math.radians(yaw_deg))
    if Veff <= 0:
        return 0.0
    lam = lambda_opt(beta_deg)
    cp_val = cp(lam, beta_deg)
    P_wind = 0.5 * RHO * A * Veff**3      # W
    return (cp_val * P_wind) / 1000.0     # kW


# --- Electrical power (after efficiency & rated cap) ---
def electrical_power(V_ms, yaw_deg, beta_deg):
    Pm = mechanical_power(V_ms, yaw_deg, beta_deg)
    Pelec = Pm * ETA
    return min(Pelec, P_RATED)


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
        # 22 : max rotor speed (rpm)

        client.write_coils(0, [True, True], slave=UNIT)
        client.write_registers(0, [0, 0, 0, 0, 0], slave=UNIT)
        client.write_registers(10, [0, 0], slave=UNIT)
        client.write_registers(20, [4, 25, RPM_MAX], slave=UNIT)
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

            coils = client.read_coils(address=0, count=2, slave=UNIT).bits
            coils = coils[:2]
            registers = client.read_holding_registers(
                address=0,
                count=12,
                slave=UNIT
            ).registers
            registers = registers[:12]

            speed_min, speed_max, max_rotor_speed = client.read_holding_registers(
                address=20,
                count=3,
                slave=UNIT
            ).registers

            broken = client.read_discrete_inputs(
                address=40,
                count=1,
                slave=UNIT
            ).bits[0]

            speed = int(open(WIND_SPEED_FILE, "r").read())
            registers[1] = speed

            yaw = randint(1, 2)
            registers[3] = yaw
            pitch = randint(10, 20)
            registers[0] = pitch

            rotor_speed = rpm(speed, yaw, pitch, max_rotor_speed)
            registers[2] = rotor_speed

            # broken
            if broken:
                print("[broken eolienne]")
                # set all values to 0
                client.write_coils(address=0, values=[False]*50, slave=UNIT)
                client.write_registers(address=0, values=[0]*50, slave=UNIT)
                continue
            # manual stop
            if not coils[0]:
                print("[stop manually]")
                registers[0] = 0  # pitch
                registers[2] = 0  # rotor speed
                registers[3] = 0  # yaw
                registers[10] = 0  # mechanical power
                registers[11] = 0  # electrical power
                client.write_registers(address=0, values=registers, slave=UNIT)
                continue
            # wind speed too slow/quick
            if speed < speed_min or speed > speed_max:
                print(f"[stop due to the wind speed] ({registers[0]} m/s)")
                coils[1] = False
                client.write_coil(address=1, value=False, slave=UNIT)
                registers[0] = 0  # pitch
                registers[2] = 0  # rotor speed
                registers[3] = 0  # yaw
                registers[10] = 0  # mechanical power
                registers[11] = 0  # electrical power
                client.write_registers(address=0, values=registers, slave=UNIT)
                continue
            # rotor speed too high
            if rotor_speed > max_rotor_speed:
                print(f"[stop due to rotor RPM to high] ({rotor_speed} rpm (max {max_rotor_speed} rpm))")
                coils[1] = False
                client.write_coil(address=1, value=False, slave=UNIT)
                registers[0] = 0  # pitch
                registers[2] = 0  # rotor speed
                registers[3] = 0  # yaw
                registers[10] = 0  # mechanical power
                registers[11] = 0  # electrical power
                client.write_registers(address=0, values=registers, slave=UNIT)
                continue

            # unwanted case
            # Wind speed > SURVIVAL_WIND_SPEED m/s will break the eolienne
            if speed > SURVIVAL_WIND_SPEED:
                broken = True
                print("[wind breaks the eolienne]")
                # signal Server that eolienne is broken
                with open(BROKEN_FILE, "w") as f:
                    f.write("true")
                registers[0] = 0  # pitch
                registers[2] = 0  # rotor speed
                registers[3] = 0  # yaw
                registers[10] = 0  # mechanical power
                registers[11] = 0  # electrical power
                client.write_registers(address=0, values=registers, slave=UNIT)
                continue

            # unwanted case
            # Rotor speed > max rotor speed will break the eolienne
            if rotor_speed > RPM_MAX:
                broken = True
                print("[rotor breaks the eolienne]")
                # signal Server that eolienne is broken
                with open(BROKEN_FILE, "w") as f:
                    f.write("true")
                registers[0] = 0  # pitch
                registers[2] = 0  # rotor speed
                registers[3] = 0  # yaw
                registers[10] = 0  # mechanical power
                registers[11] = 0  # electrical power
                client.write_registers(address=0, values=registers, slave=UNIT)
                continue

            # otherwise, running
            coils[1] = True
            registers[10] = int(mechanical_power(speed, 0, 0))
            registers[11] = int(electrical_power(speed, 0, 0))

            client.write_coils(address=0, values=coils, slave=UNIT)
            client.write_registers(address=0, values=registers, slave=UNIT)

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

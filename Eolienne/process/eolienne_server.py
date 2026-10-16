#!/usr/bin/env python
# coding=utf8
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "eolienne_server.py"
__version__ = "1.5"

import signal
import sys
import asyncio
from random import randint
import math
import traceback

from pymodbus.constants import ExcCodes
from pymodbus.datastore import (ModbusSequentialDataBlock, ModbusServerContext,
                                ModbusDeviceContext)
from pymodbus.exceptions import NoSuchIdException
from pymodbus.logging import Log
from pymodbus.pdu import ExceptionResponse
from pymodbus.pdu.device import ModbusDeviceIdentification
from pymodbus.server import ModbusTcpServer
from pymodbus.server.requesthandler import ServerRequestHandler

# Params
listen_int = "0.0.0.0"
listen_port = 502
UNIT = 0x42

WIND_SPEED_FILE = "/tmp/wind.txt"

# PyModbus function codes
FC_DI = 2
FC_CO = 1
FC_IR = 4
FC_HO = 3

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


async def init():
    devices = {
        UNIT: ModbusDeviceContext(
            di=ModbusSequentialDataBlock(0, [0]*50),
            co=ModbusSequentialDataBlock(0, [0]*50),
            hr=ModbusSequentialDataBlock(0, [0]*50),
            ir=ModbusSequentialDataBlock(0, [0]*50)
        )
    }
    context = ModbusServerContext(devices=devices, single=False)

    # Coils
    # 0 : manual status
    # 1 : auto status
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

    identity = ModbusDeviceIdentification()
    identity.VendorName = "HAXOM"
    identity.ProductCode = "SIMU-TURBOELEC"
    identity.VendorUrl = "https://github.com/haxom/simics/"
    identity.ProductName = "SIMU-TURBOELEC-EOLIENNE"
    identity.ModelName = "EOLIENNE"
    identity.MajorMinorRevision = "1.5.0"

    await asyncio.gather(
        update_physical_routine(context),
        run_server(context, identity, (listen_int, listen_port)),
    )


class EolienneRequestHandler(ServerRequestHandler):
    """Valide l'Unit Identifier avant de traiter chaque requête.

    Depuis pymodbus 3.12 la validation est faite dans chaque PDU, et certains
    (0x11 Report Device Id, 0x2B Read Device Identification, diagnostics...)
    l'ignorent : le serveur répondait alors à n'importe quel unit id, ce qui
    cassait le brute-force de ``nmap modbus-discover``. On la refait globalement
    ici. L'unité 0 (broadcast) est un alias de l'automate, et une unité inconnue
    reçoit une erreur immédiate (code fonction 0x80) que les scanners ignorent,
    donc sans timeout.
    """

    async def handle_request(self):
        if not self.last_pdu:
            return
        try:
            # L'unité 0 est un alias de UNIT (ne pas l'ajouter au contexte : son
            # repli "catch-all" ferait répondre le serveur à TOUS les unit id).
            target = UNIT if self.last_pdu.dev_id == 0 else self.last_pdu.dev_id
            self.server.context[target]  # NoSuchIdException si unit id inconnu
            response = await self.last_pdu.datastore_update(self.server.context, target)
        except NoSuchIdException:
            Log.error("requested device id does not exist: {}", self.last_pdu.dev_id)
            response = ExceptionResponse(0x00, ExcCodes.GATEWAY_NO_RESPONSE)
        except Exception as exc:  # pylint: disable=broad-except
            Log.error("Datastore unable to fulfill request: {}; {}", exc, traceback.format_exc())
            response = ExceptionResponse(self.last_pdu.function_code, ExcCodes.DEVICE_FAILURE)

        response.transaction_id = self.last_pdu.transaction_id
        response.dev_id = self.last_pdu.dev_id
        self.server_send(response, self.last_addr)


class EolienneTcpServer(ModbusTcpServer):
    """Serveur Modbus TCP utilisant :class:`EolienneRequestHandler`."""

    def callback_new_connection(self):
        return EolienneRequestHandler(
            self, self.trace_packet, self.trace_pdu, self.trace_connect
        )


async def run_server(context, identity, address):
    print(f"Modbus slave launched on {address}")
    await EolienneTcpServer(
        context=context,
        identity=identity,
        address=address,
    ).serve_forever()


async def update_physical_routine(context):
    # Meta broken state
    broken = False

    while not broken:
        # Lecture de la vitesse du vent (cm/s), écrite dans /tmp/wind.txt par
        # wind.py. Si le fichier n'existe pas encore (démarrage) ou contient
        # une valeur invalide, on retente la seconde suivante sans crasher.
        try:
            with open(WIND_SPEED_FILE) as wind_file:
                speed = int(wind_file.read())  # cm/s
        except (FileNotFoundError, ValueError) as err:
            print(f"[warn] can't read wind speed ({err}), retrying in 1s")
            await asyncio.sleep(1)
            continue

        pitch = randint(10, 20)
        yaw = randint(1, 2)
        rotor_speed = rpm(speed/100, yaw, pitch, RPM_MAX)

        power_mec = int(mechanical_power(speed/100, yaw, 0))
        power_elec = int(electrical_power(speed/100, yaw, 0))

        # manage status
        status_manual, status_auto = context[UNIT].getValues(
            func_code=FC_CO,
            address=0,
            count=2,
        )

        if status_manual == 0 or status_auto == 0:
            rotor_speed = 0
            power_mec = 0
            power_elec = 0

        # update holding registers - captors
        context[UNIT].setValues(
            func_code=FC_HO,
            address=0,
            values=[
                pitch,
                speed,
                rotor_speed,
                yaw,
            ]
        )
        # update holding registers - powers
        context[UNIT].setValues(
            func_code=FC_HO,
            address=10,
            values=[
                power_mec,
                power_elec,
            ]
        )

        # check broken scenari
        # [1] Wind speed > SURVIVAL_WIND_SPEED m/s will break the eolienne
        if speed/100 > SURVIVAL_WIND_SPEED:
            broken = True
            print("[wind breaks the eolienne]")

        # [2] Rotor speed > max rotor speed will break the eolienne
        if rotor_speed > RPM_MAX:
            broken = True
            print("[rotor breaks the eolienne]")

        if broken:
            # set broken status
            context[UNIT].setValues(
                func_code=FC_DI,
                address=40,
                values=[True],
            )

            # reset holding registers values
            context[UNIT].setValues(
                func_code=FC_HO,
                address=0,
                values=[0]*50
            )
        await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(init())
    except Exception as err:
        print("[error] Can't init Modbus server ...")
        print(f"[error] {err}")
        print("[error] exiting...")
        sys.exit(1)

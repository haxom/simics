#!/usr/bin/env python3
# coding=utf8
"""
Processus d'automatisation de l'ascenseur de maintenance
Fait le pont entre le Modbus (éolienne) et le S7comm (ascenseur) :

  - si l'éolienne tourne (pas d'arrêt manuel), l'ascenseur est arrêté ;
  - si l'éolienne a été (re)démarrée alors que l'ascenseur n'était pas
    en bas, la nacelle est déclarée cassée (alarme latchée) ;
  - en mode maintenance, le processus ne touche pas à DB1 pour ne pas
    écraser les commandes envoyées par l'API.

Le processus s'authentifie auprès de l'automate (mot de passe S7) pour
pouvoir lire/écrire DB1.
"""
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "ascenseur_process.py"
__version__ = "3.0"

import os
import signal
import sys
import struct
import time
from pymodbus.client import ModbusTcpClient
from snap7.client import Client

# ======================================================================
# Mot de passe S7comm (commun aux process -> à garder synchronisé)
# ======================================================================
S7_PASSWORD = os.environ.get("S7_PASSWORD", "maint01")

# ======================================================================
# Schéma de la DB1 (commun aux process -> à garder synchronisé)
# ======================================================================
DB1_SIZE = 10

# Zones d'écriture (pour éviter tout recouvrement entre processus)
CMD_BYTE = 0        # octet des commandes (API / interlock)
SENSOR_BYTE = 1     # premier octet des capteurs (simulateur)
ALARM_BYTE = 9      # octet d'alarme (interlock)

# --- Bits de commande (octet 0) ---
DB1_MOTOR_UP = 2
DB1_MOTOR_DOWN = 3

# --- Registres / octet d'état ---
DB1_POSITION = 2    # mot (2 octets)

# --- Bit d'alarme (octet ALARM_BYTE) ---
DB1_NACELLE_BROKEN = 0


def get_bool(data, byte_offset, bit_offset):
    return bool(data[byte_offset] & (1 << bit_offset))


def set_bool(data, byte_offset, bit_offset, value):
    if value:
        data[byte_offset] |= (1 << bit_offset)
    else:
        data[byte_offset] &= ~(1 << bit_offset)


def get_int(data, offset):
    return struct.unpack('>h', data[offset:offset + 2])[0]


def nacelle_should_break(running, position):
    """Vrai si l'éolienne tourne alors que l'ascenseur n'est pas en bas.

    C'est la situation dangereuse : l'éolienne a été (re)démarrée pendant
    une maintenance, alors que la nacelle n'était pas revenue au sol.
    """
    return bool(running) and position > 0


# Configuration
MODBUS_HOST = "127.0.0.1"
MODBUS_PORT = 502
MODBUS_UNIT = 0x42
S7_HOST = "127.0.0.1"
S7_RACK = 0
S7_SLOT = 1

UPDATE_INTERVAL = 0.5


def signal_handler(sig, frame):
    print("CTRL+C pressed, exiting...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def main():
    modbus = ModbusTcpClient(host=MODBUS_HOST, port=MODBUS_PORT)
    s7 = Client()

    while True:
        try:
            if not modbus.connected:
                modbus.connect()

            result = modbus.read_coils(
                address=0, count=2, device_id=MODBUS_UNIT
            )
            if result.isError():
                raise IOError(f"Lecture Modbus en erreur: {result}")
            status_manual = result.bits[0]

            # Interlock : seulement si l'éolienne est EN MARCHE
            if status_manual:  # True = éolienne en marche
                if not s7.get_connected():
                    s7.connect(S7_HOST, S7_RACK, S7_SLOT)
                    s7.set_session_password(S7_PASSWORD)
                data = s7.db_read(1, 0, DB1_SIZE)

                # Arrêt de l'ascenseur (octet 0 = commandes)
                cmd = data[CMD_BYTE:CMD_BYTE + 1]
                set_bool(cmd, 0, DB1_MOTOR_UP, False)
                set_bool(cmd, 0, DB1_MOTOR_DOWN, False)
                s7.db_write(1, CMD_BYTE, cmd)

                # Démarrage hors procédure : éolienne en marche avec
                # l'ascenseur qui n'est pas en bas -> nacelle cassée (latch)
                position = get_int(data, DB1_POSITION)
                if nacelle_should_break(True, position) \
                        and not get_bool(data, ALARM_BYTE, DB1_NACELLE_BROKEN):
                    alarm = data[ALARM_BYTE:ALARM_BYTE + 1]
                    set_bool(alarm, 0, DB1_NACELLE_BROKEN, True)
                    s7.db_write(1, ALARM_BYTE, alarm)
                    print("[ascenseur_process] NACELLE CASSÉE : "
                          "éolienne démarrée avec l'ascenseur en haut")

                print("[ascenseur_process] Éolienne en marche -> ascenseur arrêté")

        except Exception as e:
            print(f"[ascenseur_process] Erreur: {e}")
            modbus.close()
            s7 = Client()

        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# coding=utf8
"""
Schéma de la DB1 de l'ascenseur et helpers d'accès (commun aux process).

Toutes les valeurs partagées entre les processus de l'ascenseur sont
centralisées ici : le serveur S7comm (ascenseur_server.py), l'interlock
(ascenseur_process.py) et l'API REST (ascenseur_api.py) importent ce
module, toute modification du schéma se fait donc en un seul endroit.

  - le mot de passe S7comm, lu dans la variable d'environnement
    ``S7_PASSWORD`` (configurable dans le Dockerfile, comme
    ``OPERATOR_PWD`` pour l'IHM) ;
  - le schéma de la DB1 : les commandes (octet 0), les capteurs
    (octet 1 et suivants) et l'alarme (octet 9) sont séparés, chaque
    processus n'écrit que les octets qu'il possède, ce qui évite les
    écritures concurrentes (lost update) sur DB1 ;
  - les helpers d'accès aux booléens et aux mots big-endian.
"""
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "elevator_common.py"
__version__ = "1.0"

import os
import struct

# ======================================================================
# Mot de passe S7comm (identique pour tous les process)
# ======================================================================
# L'automate exige un mot de passe (USERDATA groupe 5, sous-fonction 1)
# avant toute lecture, écriture ou commande PLC. Limité à 8 caractères ASCII.
S7_PASSWORD = os.environ.get("S7_PASSWORD", "maint01")

# ======================================================================
# Schéma de la DB1
# ======================================================================
DB1_SIZE = 10

# Zones d'écriture (pour éviter tout recouvrement entre processus)
CMD_BYTE = 0        # octet des commandes (API / interlock)
SENSOR_BYTE = 1     # premier octet des capteurs (simulateur)
ALARM_BYTE = 9      # octet d'alarme (interlock)

# --- Bits de commande (octet 0) ---
DB1_MOTOR_UP = 2
DB1_MOTOR_DOWN = 3

# --- Bits capteurs (octet 1) ---
DB1_POS_HIGH = 0
DB1_POS_LOW = 1
DB1_DOOR_CLOSED = 2

# --- Registres / octet d'état ---
DB1_POSITION = 2    # mot (2 octets)
DB1_SPEED = 4       # mot (2 octets)
DB1_STATE = 8       # octet

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


def set_int(data, offset, value):
    struct.pack_into('>h', data, offset, value)

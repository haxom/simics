#!/usr/bin/env python3
# coding=utf8
"""
Automate (PLC) de l'ascenseur de maintenance : serveur S7comm + simulation.

Ce fichier contient l'automate complet :

  - un serveur S7comm (python-snap7) qui héberge la DB1 et exige un mot de
    passe pour lire/écrire/commander (USERDATA groupe 5, sous-fonction 1) ;
  - la simulation physique de l'ascenseur, qui tourne dans le même processus
    et met à jour DB1 en mémoire (comme le programme d'un automate réel).

La physique n'écrit que les octets 1..8 (capteurs, position, vitesse, état) ;
elle ne réécrit jamais l'octet 0 (commandes) ni l'octet 9 (alarme) : un seul
écrivain par octet, donc pas d'écrasement concurrent.

Le mot de passe est lu dans la variable d'environnement ``S7_PASSWORD``
(configurable dans le Dockerfile, comme ``OPERATOR_PWD`` pour l'IHM).
"""
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "ascenseur_server.py"
__version__ = "4.0"

import hmac
import os
import signal
import struct
import sys
import threading
import time

from snap7.datatypes import S7Area
from snap7.server import Server
from snap7.s7protocol import (
    S7Function,
    S7PDUType,
    S7UserDataGroup,
    S7UserDataSubfunction,
)
from snap7.type import SrvArea

# --- Configuration S7comm ---
LISTEN_ADDR = "0.0.0.0"
LISTEN_PORT = 102
S7_AREA_SIZE = 100      # taille de la zone DB1 exposée par le serveur

# Code de retour S7 « accès à l'objet non autorisé ».
S7_ACCESS_DENIED = 0x03
# Erreur S7 (classe 0x84) : zone/opération interdite.
S7_ERR_FUNCTION = 0x8404

# ======================================================================
# Mot de passe S7comm (commun aux process -> à garder synchronisé)
# ======================================================================
# L'automate exige un mot de passe (USERDATA groupe 5, sous-fonction 1)
# avant toute lecture, écriture ou commande PLC. Limité à 8 caractères ASCII.
S7_PASSWORD = os.environ.get("S7_PASSWORD", "maint01")
MAX_PASSWORD_LEN = 8


def encode_password(password):
    """Encode un mot de passe S7 dans le format filaire (8 octets).

    Algorithme S7/Snap7 : padding à 8 octets avec des espaces, XOR avec
    0x55, puis chaînage de chaque octet avec celui situé deux positions
    avant (``enc[i] = raw[i] ^ 0x55 ^ enc[i-2]``).
    """
    raw = password.encode("ascii")
    if not 1 <= len(raw) <= MAX_PASSWORD_LEN:
        raise ValueError("Le mot de passe S7 doit faire 1 à 8 caractères ASCII")
    raw = raw.ljust(MAX_PASSWORD_LEN, b" ")
    encoded = bytearray(MAX_PASSWORD_LEN)
    for i in range(MAX_PASSWORD_LEN):
        encoded[i] = raw[i] ^ 0x55 ^ (encoded[i - 2] if i >= 2 else 0)
    return bytes(encoded)


def decode_password(encoded):
    """Inverse de :func:`encode_password` (analyse de capture réseau)."""
    if len(encoded) != MAX_PASSWORD_LEN:
        raise ValueError("Le mot de passe S7 encodé doit faire 8 octets")
    raw = bytearray(MAX_PASSWORD_LEN)
    for i in range(MAX_PASSWORD_LEN):
        raw[i] = encoded[i] ^ 0x55 ^ (encoded[i - 2] if i >= 2 else 0)
    return raw.rstrip(b" ").decode("ascii", errors="replace")


# ======================================================================
# Schéma de la DB1 (commun aux process -> à garder synchronisé)
# ======================================================================
# Les commandes (octet 0), les capteurs (octet 1 et suivants) et l'alarme
# (octet 9) sont séparés : chaque processus n'écrit que les octets qu'il
# possède, ce qui évite les écritures concurrentes (lost update) sur DB1.
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


# ======================================================================
# Logique de l'ascenseur (mouvement)
# ======================================================================
# États
STATE_STOPPED = 0
STATE_UP = 1
STATE_DOWN = 2
STATE_ERROR = 3
STATE_BROKEN = 4

# Mouvement : POSITION_STEP % par cycle -> course complète en ~10 s
POSITION_STEP = 5
ELEVATOR_SPEED = 10     # 0-50 -> 0.0-5.0 m/s à l'affichage (speed / 10)

POSITION_MIN = 0
POSITION_MAX = 100

UPDATE_INTERVAL = 0.5   # secondes entre deux mises à jour


def step(position, motor_up, motor_down, broken):
    """Calcule (état, vitesse, nouvelle position) pour un cycle.

    - `broken` : nacelle cassée -> mouvement figé, état CASSÉ.
    - commande des deux moteurs simultanément -> état ERREUR.
    """
    if broken:
        return STATE_BROKEN, 0, position

    if not motor_up and not motor_down:
        return STATE_STOPPED, 0, position

    if motor_up and not motor_down:
        if position < POSITION_MAX:
            return STATE_UP, ELEVATOR_SPEED, min(POSITION_MAX, position + POSITION_STEP)
        return STATE_STOPPED, 0, position

    if motor_down and not motor_up:
        if position > POSITION_MIN:
            return STATE_DOWN, ELEVATOR_SPEED, max(POSITION_MIN, position - POSITION_STEP)
        return STATE_STOPPED, 0, position

    # Les deux moteurs commandés en même temps
    return STATE_ERROR, 0, position


# ======================================================================
# Serveur S7comm protégé par mot de passe
# ======================================================================
class PasswordProtectedServer(Server):
    """Serveur S7comm exigeant un mot de passe pour lire/écrire/commander.

    Restrictions d'accès (comme sur un automate Siemens réel) : sans le mot
    de passe S7, la lecture, l'écriture et les commandes PLC (arrêt /
    contrôle) sont refusées avec le code S7 ``0x03``.
    """

    def __init__(self, password, **kwargs):
        super().__init__(**kwargs)
        # Valide le mot de passe dès le démarrage (1 à 8 caractères ASCII).
        encode_password(password)
        self.password = password
        # État d'authentification par connexion : le serveur traite chaque
        # client dans son propre thread, on utilise donc un stockage local.
        self._tls = threading.local()

    # ------------------------------------------------------------------
    # État d'authentification (local à la connexion / au thread)
    # ------------------------------------------------------------------
    def _is_authenticated(self):
        return getattr(self._tls, "authenticated", False)

    def _set_authenticated(self, value):
        self._tls.authenticated = value

    def _client(self):
        return getattr(self._tls, "address", "?")

    def _process_request(self, request_data, client_address):
        # Mémorise l'adresse du client courant pour les journaux.
        self._tls.address = client_address
        return super()._process_request(request_data, client_address)

    # ------------------------------------------------------------------
    # Authentification (USERDATA groupe Security)
    # ------------------------------------------------------------------
    def _handle_security(self, request, userdata_params, client_address):
        subfunction = userdata_params.get("subfunction", 0)

        if subfunction == S7UserDataSubfunction.SET_SESSION_PASSWORD:
            raw = (request.get("data") or {}).get("data", b"")
            if len(raw) == 8 and hmac.compare_digest(raw, encode_password(self.password)):
                self._set_authenticated(True)
                print(f"[S7] Authentification reussie ({client_address})")
                return self._build_userdata_success_response(request, userdata_params, b"")

            self._set_authenticated(False)
            candidate = decode_password(raw) if len(raw) == 8 else ""
            print(f"[S7] Authentification refusee ({client_address}) "
                  f"- mot de passe tente : {candidate!r}")
            return self._build_security_failure(request, userdata_params)

        if subfunction == S7UserDataSubfunction.CLEAR_SESSION_PASSWORD:
            self._set_authenticated(False)
            print(f"[S7] Session fermee ({client_address})")
            return self._build_userdata_success_response(request, userdata_params, b"")

        # Sous-fonction de sécurité inconnue.
        return self._build_userdata_error_response(request, 0x8104)

    def _build_security_failure(self, request, userdata_params):
        """Réponse USERDATA/Security indiquant un mot de passe invalide."""
        subfunction = userdata_params.get("subfunction", 0)
        seq = userdata_params.get("sequence", 0)

        param_data = struct.pack(
            ">BBBBBBBBBBBB",
            0x00,  # Réservé
            0x01,  # Nombre de paramètres
            0x12,  # En-tête type/longueur
            0x08,  # Longueur (8 octets suivants)
            0x12,  # Méthode (réponse)
            0x80 | int(S7UserDataGroup.SECURITY),  # Type (réponse) | Groupe
            int(subfunction),  # Sous-fonction
            seq,  # Séquence
            0x00,  # Référence data unit
            0x00,  # Dernier data unit
            0x00,  # Code erreur (haut)
            0x00,  # Code erreur (bas)
        )
        # Section data : code de retour 0x03 = accès non autorisé.
        data_section = struct.pack(">BBH", S7_ACCESS_DENIED, 0x00, 0x0000)
        header = struct.pack(
            ">BBHHHH",
            0x32,  # Identifiant protocole
            S7PDUType.USERDATA,
            0x0000,  # Réservé
            request.get("sequence", 0),
            len(param_data),
            len(data_section),
        )
        return header + param_data + data_section

    # ------------------------------------------------------------------
    # Restrictions d'accès en lecture
    # ------------------------------------------------------------------
    def _read_from_memory_area(self, area, db_number, start, count):
        if not self._is_authenticated():
            print(f"[S7] Lecture refusee ({self._client()}) - non authentifie")
            return (S7_ACCESS_DENIED, bytearray())
        return super()._read_from_memory_area(area, db_number, start, count)

    # ------------------------------------------------------------------
    # Restrictions d'accès en écriture
    # ------------------------------------------------------------------
    def _handle_write_area(self, request, client_address):
        if not self._is_authenticated():
            print(f"[S7] Ecriture refusee ({client_address}) - non authentifie")
            return self._build_denied_write(request)
        return super()._handle_write_area(request, client_address)

    def _build_denied_write(self, request):
        """Réponse d'écriture refusée (code retour 0x03)."""
        header = struct.pack(
            ">BBHHHHBB",
            0x32,
            S7PDUType.ACK_DATA,
            0x0000,
            request["sequence"],
            0x0002,  # Longueur paramètres
            0x0001,  # Longueur data
            0x00,  # Classe d'erreur
            0x00,  # Octet d'erreur
        )
        parameters = struct.pack(">BB", S7Function.WRITE_AREA, 0x01)
        data_section = struct.pack(">B", S7_ACCESS_DENIED)
        return header + parameters + data_section

    # ------------------------------------------------------------------
    # Restrictions d'accès aux commandes PLC
    # ------------------------------------------------------------------
    def _handle_plc_control(self, request, client_address):
        if not self._is_authenticated():
            print(f"[S7] Commande PLC refusee ({client_address}) - non authentifie")
            return self._build_error_response(request, S7_ERR_FUNCTION)
        return super()._handle_plc_control(request, client_address)

    def _handle_plc_stop(self, request, client_address):
        if not self._is_authenticated():
            print(f"[S7] Arret PLC refuse ({client_address}) - non authentifie")
            return self._build_error_response(request, S7_ERR_FUNCTION)
        return super()._handle_plc_stop(request, client_address)

    # ------------------------------------------------------------------
    # Cohérence : annonce le niveau de protection dans le SZL 0x0232
    # ------------------------------------------------------------------
    def _get_szl_data(self, szl_id, szl_index):
        if szl_id == 0x0232:
            # Niveau 3 = restriction en modification ET en lecture
            # (coherent avec le verrouillage lecture/ecriture/commandes PLC).
            return struct.pack(">HHHHH", 3, 3, 3, 3, 3)
        return super()._get_szl_data(szl_id, szl_index)


# ======================================================================
# Simulation physique (dans le même processus que le serveur)
# ======================================================================
class AscenseurSimulator:
    """Programme de l'automate : met à jour DB1 directement en mémoire.

    L'accès à la mémoire se fait sous le verrou de zone du serveur, le même
    que celui utilisé par le serveur pour les accès réseau (pas de course).
    """

    def __init__(self, db1, lock):
        self.db1 = db1
        self.lock = lock
        self.position = 0.0
        self.speed = 0
        self.state = STATE_STOPPED

    def update(self):
        with self.lock:
            motor_up = get_bool(self.db1, CMD_BYTE, DB1_MOTOR_UP)
            motor_down = get_bool(self.db1, CMD_BYTE, DB1_MOTOR_DOWN)
            broken = get_bool(self.db1, ALARM_BYTE, DB1_NACELLE_BROKEN)

            self.state, self.speed, self.position = step(
                self.position, motor_up, motor_down, broken
            )

            # Octets possédés par le simulateur (1..8)
            set_bool(self.db1, SENSOR_BYTE, DB1_POS_HIGH, self.position >= POSITION_MAX)
            set_bool(self.db1, SENSOR_BYTE, DB1_POS_LOW, self.position <= POSITION_MIN)
            set_bool(self.db1, SENSOR_BYTE, DB1_DOOR_CLOSED, True)
            set_int(self.db1, DB1_POSITION, int(self.position))
            set_int(self.db1, DB1_SPEED, self.speed)
            self.db1[DB1_STATE] = self.state


def signal_handler(sig, frame):
    print("CTRL+C pressed, exiting...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def main():
    server = PasswordProtectedServer(S7_PASSWORD, log=False)
    db1 = bytearray(S7_AREA_SIZE)
    server.register_area(SrvArea.DB, 1, db1)
    # Même verrou que le serveur : la physique et le réseau ne se marchent pas dessus.
    lock = server.area_locks[(S7Area.DB, 1)]
    server.start_to(LISTEN_ADDR, LISTEN_PORT)
    print(f"Serveur S7comm protege demarre sur {LISTEN_ADDR}:{LISTEN_PORT} "
          f"(mot de passe requis pour lecture/ecriture/commandes)")
    print("[SIMU] Démarrage de la simulation ascenseur")

    simulator = AscenseurSimulator(db1, lock)
    try:
        while True:
            try:
                simulator.update()
            except Exception as e:
                print(f"[SIMU] Erreur: {e}")
            time.sleep(UPDATE_INTERVAL)
    finally:
        server.stop()


if __name__ == "__main__":
    main()

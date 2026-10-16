#!/usr/bin/env python3
# coding=utf8
"""
API REST pour l'ascenseur de maintenance
Fait le pont entre l'IHM web (PHP) et le serveur S7comm.

L'API n'écrit que l'octet 0 de DB1 (commandes) pour ne jamais écraser les
capteurs/position tenus par le simulateur. Elle s'authentifie auprès de
l'automate (mot de passe S7, défini avec le schéma de la DB1 dans
``elevator_common.py``).
"""
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "ascenseur_api.py"
__version__ = "3.0"

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from snap7.client import Client

from elevator_common import (
    S7_PASSWORD,
    DB1_SIZE,
    CMD_BYTE, SENSOR_BYTE, ALARM_BYTE,
    DB1_MOTOR_UP, DB1_MOTOR_DOWN,
    DB1_POS_HIGH, DB1_POS_LOW, DB1_DOOR_CLOSED,
    DB1_POSITION, DB1_SPEED, DB1_STATE,
    DB1_NACELLE_BROKEN,
    get_bool, set_bool, get_int,
)


S7_HOST = "127.0.0.1"
S7_RACK = 0
S7_SLOT = 1
API_PORT = 8080

_client = None


def get_client():
    """Connexion persistante au serveur S7 (reconnexion si nécessaire)."""
    global _client
    if _client is None:
        _client = Client()
    if not _client.get_connected():
        _client.connect(S7_HOST, S7_RACK, S7_SLOT)
        _client.set_session_password(S7_PASSWORD)
    return _client


def read_ascenseur_data():
    data = get_client().db_read(1, 0, DB1_SIZE)

    return {
        "position": get_int(data, DB1_POSITION),
        "speed": get_int(data, DB1_SPEED) / 10.0,
        "state": data[DB1_STATE],
        "pos_high": get_bool(data, SENSOR_BYTE, DB1_POS_HIGH),
        "pos_low": get_bool(data, SENSOR_BYTE, DB1_POS_LOW),
        "door_closed": get_bool(data, SENSOR_BYTE, DB1_DOOR_CLOSED),
        "nacelle_broken": get_bool(data, ALARM_BYTE, DB1_NACELLE_BROKEN),
    }


def write_command(cmd):
    print(f"[API] Commande reçue: {cmd}")
    client = get_client()
    # Seul l'octet 0 (commandes) est lu puis réécrit
    data = client.db_read(1, CMD_BYTE, 1)

    if cmd == "up":
        set_bool(data, 0, DB1_MOTOR_UP, True)
        set_bool(data, 0, DB1_MOTOR_DOWN, False)
    elif cmd == "down":
        set_bool(data, 0, DB1_MOTOR_UP, False)
        set_bool(data, 0, DB1_MOTOR_DOWN, True)
    elif cmd == "stop":
        set_bool(data, 0, DB1_MOTOR_UP, False)
        set_bool(data, 0, DB1_MOTOR_DOWN, False)

    client.db_write(1, CMD_BYTE, data)
    print(f"[API] Commande {cmd} appliquée")


class AscenseurHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/status":
            try:
                data = read_ascenseur_data()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/command":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                cmd = json.loads(body).get("command", "")
                if cmd in ("up", "down", "stop"):
                    write_command(cmd)
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"ok")
                else:
                    self.send_response(400)
                    self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(404)
            self.end_headers()


def main():
    server = HTTPServer(("127.0.0.1", API_PORT), AscenseurHandler)
    print(f"API REST ascenseur démarrée sur le port {API_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()

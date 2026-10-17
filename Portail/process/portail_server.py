#!/usr/bin/env python
# coding=utf8
"""
Automate du portail électrique : serveur Modbus TCP.

Porté à l'API pymodbus 3.x (comme eolienne_server.py) : ModbusDeviceContext,
ModbusTcpServer asyncio, et la même validation globale de l'Unit Identifier
(sous-classe ServerRequestHandler). Depuis pymodbus 3.12 la validation est
faite dans chaque PDU, et certains (0x11 Report Device Id, 0x2B Read Device
Identification, diagnostics...) l'ignorent : le serveur répondrait alors à
n'importe quel unit id, ce qui casse le brute-force de ``nmap
modbus-discover``. On la refait globalement ici. L'unité 0 (broadcast) est
un alias de l'automate, et une unité inconnue reçoit une erreur immédiate
(code fonction 0x80) que les scanners ignorent, donc sans timeout.
"""
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "portail_server.py"
__version__ = "1.4"

import asyncio
import signal
import sys
import traceback

from pymodbus.constants import ExcCodes
from pymodbus.datastore import (ModbusSequentialDataBlock, ModbusServerContext,
                                ModbusDeviceContext)
from pymodbus.pdu.device import ModbusDeviceIdentification
from pymodbus.exceptions import NoSuchIdException
from pymodbus.logging import Log
from pymodbus.pdu import ExceptionResponse
from pymodbus.server import ModbusTcpServer
from pymodbus.server.requesthandler import ServerRequestHandler

# Params
listen_int = "0.0.0.0"
listen_port = 502
UNIT = 0x2d


def signal_handler(sig, frame):
    print("CTRL+C pressed, exiting...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


class PortailRequestHandler(ServerRequestHandler):
    """Valide l'Unit Identifier avant de traiter chaque requête.

    Cf. docstring du module et eolienne_server.py (même pattern) : l'unité
    0 est un alias de UNIT (ne pas l'ajouter au contexte : son repli
    "catch-all" ferait répondre le serveur à TOUS les unit id), une unité
    inconnue reçoit une erreur immédiate sans timeout.
    """

    async def handle_request(self):
        if not self.last_pdu:
            return
        try:
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


class PortailTcpServer(ModbusTcpServer):
    """Serveur Modbus TCP utilisant :class:`PortailRequestHandler`."""

    def callback_new_connection(self):
        return PortailRequestHandler(
            self, self.trace_packet, self.trace_pdu, self.trace_connect
        )


async def init():
    devices = {
        UNIT: ModbusDeviceContext(
            di=ModbusSequentialDataBlock(0, [17]*100),
            co=ModbusSequentialDataBlock(0, [17]*100),
            hr=ModbusSequentialDataBlock(0, [17]*100),
            ir=ModbusSequentialDataBlock(0, [17]*100)
        )
    }
    context = ModbusServerContext(devices=devices, single=False)

    identity = ModbusDeviceIdentification()
    identity.VendorName = "HAXOM"
    identity.ProductCode = "SIMU-ICS-PORTAIL"
    identity.VendorUrl = "https://github.com/haxom/"
    identity.ProductName = "SIMU-ICS"
    identity.ModelName = "PORTAIL"
    identity.MajorMinorRevision = "1.4.0"

    await run_server(context, identity, (listen_int, listen_port))


async def run_server(context, identity, address):
    print(f"Modbus slave launched on {address}")
    await PortailTcpServer(
        context=context,
        identity=identity,
        address=address,
    ).serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(init())
    except Exception as err:
        print("[error] Can't init Modbus server ...")
        print(f"[error] {err}")
        print("[error] exiting...")
        sys.exit(1)

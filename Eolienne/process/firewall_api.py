#!/usr/bin/env python3
# coding=utf8
"""
Pare-feu local de l'éolienne : micro-API REST sur loopback 8081.

Gère deux chaînes iptables dédiées, TURBOELEC_IN (accrochée en 1re
position de INPUT) et TURBOELEC_OUT (sur OUTPUT), et n'écrit RIEN dans
le reste de la table : les règles système (et celles de Docker) restent
intactes, et un `iptables -F` sur nos deux chaînes ou un redémarrage du
conteneur entraîne un reset propre (nouveau round d'exercice).

Elle tourne en root dans le conteneur (via supervisord) pour disposer
des droits iptables ; firewall.php relaie les requêtes du navigateur
(qui ne peut pas joindre le loopback du conteneur).

Endpoints (relayés par firewall.php) :

  GET  /api/rules   -> règles en cours des deux chaînes (avec compteurs)
  POST /api/rules   -> {direction, action, ip?, port?, proto?}
  POST /api/delete  -> {direction, index}
  POST /api/reset   -> vide les chaînes TURBOELEC_IN / TURBOELEC_OUT

Capture réseau (PCAP à analyser dans Wireshark, pilotée depuis la page
pare-feu — le stagiaire n'a pas à ouvrir de shell dans le conteneur) :

  POST /api/capture/start -> lance tcpdump (ring 3x20 Mo sur /tmp)
  POST /api/capture/stop  -> arrête la capture (flush propre du PCAP)
  GET  /api/capture/state -> {running, size, remaining}
  GET  /api/capture/download -> télécharge le fichier le plus récent

La durée de capture est bornée (CAPTURE_MAX_SECS = 10 min) : arrêt
automatique passé ce délai, et téléchargement refusé (409) tant que le
tcpdump tourne — le PCAP en cours d'écriture serait tronqué.

direction : "in" (entrant) ou "out" (sortant)
action    : DROP / REJECT / ACCEPT
proto     : tcp / udp / any (si un port est précisé, "any" => tcp)
"""
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "firewall_api.py"
__version__ = "1.0"

import json
import os
import re
import shutil
import signal
import subprocess
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

API_PORT = 8081
CHAINS = {"in": "TURBOELEC_IN", "out": "TURBOELEC_OUT"}
BASE_CHAIN = {"in": "INPUT", "out": "OUTPUT"}
ACTIONS = ("DROP", "REJECT", "ACCEPT")
PROTOS = ("tcp", "udp", "any")

IPTABLES = shutil.which("iptables") or "/usr/sbin/iptables"
IP_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$")


def ipt(*args):
    """Exécute iptables. Retourne (rc, stdout+stderr)."""
    result = subprocess.run(
        [IPTABLES, *args], capture_output=True, text=True
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def ensure_chains():
    """Crée les chaînes dédiées et les accroche en tête de INPUT/OUTPUT."""
    for direction, chain in CHAINS.items():
        rc, out = ipt("-N", chain)
        if rc != 0 and "already exists" not in out:
            print(f"[init] impossible de créer {chain} : {out}")
        rc, out = ipt("-C", BASE_CHAIN[direction], "-j", chain)
        if rc != 0:
            rc, out = ipt("-I", BASE_CHAIN[direction], "1", "-j", chain)
            if rc != 0:
                print(f"[init] impossible d'accrocher {chain} : {out}")
                return
            print(f"[init] {chain} accrochée sur {BASE_CHAIN[direction]}")


def parse_chain_output(text):
    """Parse la sortie de `iptables -vnL <chaine> --line-numbers`."""
    rules = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 10 or not parts[0].isdigit():
            continue
        # num pkts bytes target prot opt in out source destination [extra]
        rules.append({
            "index": int(parts[0]),
            "pkts": int(parts[1]),
            "bytes": int(parts[2]),
            "action": parts[3],
            "proto": parts[4],
            "source": parts[8],
            "destination": parts[9],
            "extra": " ".join(parts[10:]),
        })
    return rules


def get_rules():
    """Liste des règles des deux chaînes, avec compteurs."""
    return {
        "in": parse_chain_output(ipt("-vnL", CHAINS["in"], "--line-numbers")[1]),
        "out": parse_chain_output(ipt("-vnL", CHAINS["out"], "--line-numbers")[1]),
    }


def add_rule(direction, action, ip=None, port=None, proto="any"):
    """Ajoute une règle en queue de chaîne dédiée.

    La chaîne est accrochée en 1re position de INPUT/OUTPUT, donc les
    nouvelles règles passent avant celles du système, quel que soit
    leur ordre dans la chaîne.
    """
    cmd = ["-A", CHAINS[direction]]
    if ip:
        # in => on filtre la source ; out => la destination
        cmd += ["-s" if direction == "in" else "-d", ip]
    if port:
        if proto == "any":
            proto = "tcp"
        cmd += ["-p", proto, "--dport", str(port)]
    elif proto != "any":
        cmd += ["-p", proto]
    cmd += ["-j", action]
    rc, out = ipt(*cmd)
    return (rc == 0, out)


def delete_rule(direction, index):
    """Supprime le numéro de ligne `index` de la chaîne dédiée."""
    pos = str(index)
    rc, out = ipt("-D", CHAINS[direction], pos)
    return (rc == 0, out)


def reset_rules():
    errs = []
    for chain in CHAINS.values():
        rc, out = ipt("-F", chain)
        if rc != 0:
            errs.append(out)
    return (not errs, "; ".join(errs))


# --- Capture réseau (exercice : PCAP à analyser dans Wireshark) ---

CAPTURE_PREFIX = "/tmp/turboelec_capture"
CAPTURE_PID = "/tmp/turboelec_capture.pid"
# Durée maximale d'une capture : au-delà le PCAP risque d'être recyclé
# par le ring (-W 3) avant téléchargement, et une capture « oubliée »
# par le stagiaire ne doit pas remplir le disque du conteneur.
CAPTURE_MAX_SECS = 600        # 10 minutes
capture_proc = None
capture_timer = None          # threading.Timer de l'arrêt automatique
capture_started = 0.0         # instant de départ (calcul de « remaining »)
CAPTURE_LOCK = threading.Lock()   # le Timer introduit un 2e thread


def capture_running():
    """True si le tcpdump de la capture tourne (verrou non tenu)."""
    return capture_proc is not None and capture_proc.poll() is None


def _auto_stop():
    """Minuteur de garde : arrêt automatique passé CAPTURE_MAX_SECS."""
    print(f"[capture] durée maximale de {CAPTURE_MAX_SECS // 60} min "
          f"atteinte : arrêt automatique", flush=True)
    capture_stop()


def capture_files():
    """Fichiers du ring tcpdump (-W 3), du plus récent au plus ancien."""
    files = []
    for suffix in ("", "0", "1", "2"):
        path = CAPTURE_PREFIX + ".pcap" + suffix
        if os.path.exists(path):
            files.append((os.path.getmtime(path), path))
    files.sort(reverse=True)
    return files


def capture_start():
    global capture_proc, capture_timer, capture_started
    with CAPTURE_LOCK:
        if capture_running():
            return True, "capture déjà en cours"
        # après un redémarrage de l'API, l'ancien tcpdump peut être orphelin :
        # le fichier .pid permet de le couper proprement avant de repartir
        try:
            with open(CAPTURE_PID) as f:
                old_pid = int(f.read())
            with open(f"/proc/{old_pid}/cmdline", "rb") as f:
                if b"turboelec_capture" not in f.read():
                    raise ValueError
            os.kill(old_pid, signal.SIGINT)
            time.sleep(1.0)   # temps de flush du PCAP par l'ancien process
        except (OSError, ValueError):
            pass
        try:
            # snaplen complet (-s 0) : le payload des beacons doit rester
            # analysable dans Wireshark ; ring -C 20 -W 3 borné à ~60 Mo
            capture_proc = subprocess.Popen(
                ["tcpdump", "-i", "eth0", "-s", "0", "-U", "-w",
                 CAPTURE_PREFIX + ".pcap", "-C", "20", "-W", "3"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            capture_proc = None
            return False, "tcpdump indisponible"
        with open(CAPTURE_PID, "w") as f:
            f.write(str(capture_proc.pid))
        # garde-fou « stagiaire qui oublie » : le même chemin qu'un arrêt
        # manuel (SIGINT -> flush propre du PCAP)
        if capture_timer is not None:
            capture_timer.cancel()
        capture_timer = threading.Timer(CAPTURE_MAX_SECS, _auto_stop)
        capture_timer.daemon = True
        capture_timer.start()
        capture_started = time.time()
        return True, "capture démarrée"


def capture_stop():
    """Arrêt du tcpdump, manuel (bouton) ou automatique (minuteur)."""
    global capture_proc, capture_timer, capture_started
    with CAPTURE_LOCK:
        # désarmé d'abord : un arrêt manuel doit court-circuiter le
        # minuteur (le SIGINT + wait s'occupent ensuite du process)
        if capture_timer is not None:
            capture_timer.cancel()
            capture_timer = None
        if capture_running():
            capture_proc.send_signal(signal.SIGINT)
            try:
                capture_proc.wait(timeout=5)   # flush du PCAP
            except subprocess.TimeoutExpired:
                capture_proc.kill()
            print(f"[capture] tcpdump coupé après "
                  f"{round(time.time() - capture_started)} s", flush=True)
            capture_proc = None
            return True, "capture arrêtée"
        return True, "aucune capture en cours"


def capture_state():
    with CAPTURE_LOCK:
        running = capture_running()
        remaining = None
        if running:
            remaining = max(0, round(CAPTURE_MAX_SECS
                                     - (time.time() - capture_started)))
        size = sum(os.path.getsize(path) for _, path in capture_files())
        return {"running": running, "size": size, "remaining": remaining}


def validate(body):
    """Valide une requête POST /api/rules. Retourne (valeurs, message)."""
    direction = body.get("direction")
    action = body.get("action")
    proto = body.get("proto", "any") or "any"
    ip = body.get("ip") or None
    port = body.get("port") or None

    if direction not in CHAINS:
        return None, "direction invalide (in/out)"
    if action not in ACTIONS:
        return None, "action invalide (DROP/REJECT/ACCEPT)"
    if ip:
        ip = str(ip)
        if not IP_RE.match(ip):
            return None, "adresse IP invalide"
        octets = ip.split("/")[0].split(".")
        if any(int(o) > 255 for o in octets):
            return None, "adresse IP invalide"
    if port is not None:
        try:
            port = int(port)
        except (TypeError, ValueError):
            return None, "port invalide"
        if not 1 <= port <= 65535:
            return None, "port invalide"
    if proto not in PROTOS:
        return None, "proto invalide (tcp/udp/any)"

    # Garde anti-self-lockout : une règle ENTRANTE sans filtre de port (elle
    # couvre tout) ou ciblant le port 80 couperait l'accès à l'IHM web du
    # pare-feu : le stagiaire se bloquerait lui-même. Refusées.
    if direction == "in" and action in ("DROP", "REJECT") and (port is None or port == 80):
        return None, ("Interdit : cette règle couperait l'accès à l'IHM (port 80). "
                      "Restreignez la source IP, ou précisez un port autre que 80.")

    return {
        "direction": direction,
        "action": action,
        "ip": ip,
        "port": port,
        "proto": proto,
    }, ""


class FirewallHandler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def _send_capture_file(self):
        """Téléchargement du fichier de capture le plus récent.

        Refusé (409) tant qu'une capture est en cours : le PCAP serait
        tronqué (flush tcpdump non effectué).
        """
        with CAPTURE_LOCK:
            running = capture_running()
            files = capture_files()
        if running:
            self._send(409, {"error": (
                "capture en cours : arrêtez-la avant de télécharger")})
            return
        if not files:
            self._send(404, {"error": "aucune capture disponible"})
            return
        try:
            with open(files[0][1], "rb") as f:
                data = f.read()
        except OSError:
            self._send(404, {"error": "capture indisponible"})
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.tcpdump.pcap")
        self.send_header("Content-Disposition",
                         'attachment; filename="turboelec_capture.pcap"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/rules":
            self._send(200, get_rules())
        elif self.path == "/api/capture/state":
            self._send(200, capture_state())
        elif self.path == "/api/capture/download":
            self._send_capture_file()
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw) if raw else {}
        except ValueError:
            self._send(400, {"ok": False, "error": "JSON invalide"})
            return

        if self.path == "/api/rules":
            values, err = validate(body)
            if err:
                self._send(400, {"ok": False, "error": err})
                return
            ok, out = add_rule(**values)
            self._send(200, {"ok": ok, "error": out if not ok else ""})
        elif self.path == "/api/delete":
            direction = body.get("direction")
            if direction not in CHAINS or not isinstance(body.get("index"), int):
                self._send(400, {"ok": False, "error": "paramètres invalides"})
                return
            ok, out = delete_rule(direction, body["index"])
            self._send(200, {"ok": ok, "error": out if not ok else ""})
        elif self.path == "/api/reset":
            ok, out = reset_rules()
            self._send(200, {"ok": ok, "error": out if not ok else ""})
        elif self.path == "/api/capture/start":
            ok, msg = capture_start()
            self._send(200, {"ok": ok, "error": msg if not ok else ""})
        elif self.path == "/api/capture/stop":
            ok, msg = capture_stop()
            self._send(200, {"ok": ok, "error": msg if not ok else ""})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        # access log discret : la page firewall.php sonde toutes les 2 s
        return


def main():
    ensure_chains()
    server = HTTPServer(("127.0.0.1", API_PORT), FirewallHandler)
    print(f"API pare-feu démarrée sur le port {API_PORT} "
          f"(chaînes {CHAINS['in']}/{CHAINS['out']})")
    server.serve_forever()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# coding=utf8
"""
Serveur C2 de la formation : collecte les beacons envoyés par le malware
déguisé des éoliennes (processus « weather_sync »).

Chaque beacon est journalisé :
  - sur stdout (visible avec `docker logs <c2>`, pratique en démo) ;
  - dans /data/c2_beacons.jsonl (historique persistant du conteneur).

Le champ src_ip du journal est l'IP source vue par le C2 : après blocage
du beacon côté pare-feu de l'éolienne, l'absence de nouveau beacon par
IP est la validation formateur de l'exercice défensif.

Endpoints :
  POST /beacon  -> beacon JSON du malware (corps quelconque, journalisé brut)
                   (SANS auth : le malware doit toujours pouvoir beaconer)
  GET  /probe   -> sonde simple (« C2 alive »), sans donnée ni auth
  GET  /        -> vue web formateur : table des beacons par IP source
                   (protégée par une mire mot de passe)
  POST /login   -> validation du mot de passe, pose un cookie de session
"""
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "c2_server.py"
__version__ = "2.0"

import hmac
import html
import json
import os
import secrets
import time
from urllib.parse import parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

LISTEN_ADDR = "0.0.0.0"
LISTEN_PORT = 4444
LOG_FILE = "/data/c2_beacons.jsonl"
REFRESH = 10          # auto-refresh (s) de la page de suivi
SILENCE_THRESHOLD = 60  # s : au-delà, une IP est affichée « bloquée »

# Mot de passe de la mire web formateur (override : ARG Docker/build-arg
# ou environment dans le docker-compose).
C2_PASSWORD = os.environ.get("C2_PASSWORD", "Ev1l_W3atherSyn4c")

# Token de session, régénéré au démarrage du serveur : un restart C2
# déconnecte les sessions ouvertes, c'est voulu.
SESSION_TOKEN = secrets.token_hex(32)

COOKIE = "turboelec_c2_session"


def log_beacon(source_ip, payload, registry):
    """Journalise un beacon sur stdout, dans le JSONL et dans le registre."""
    entry = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "src_ip": source_ip,
        "payload": payload,
    }
    line = json.dumps(entry, ensure_ascii=False)
    print(f"[beacon] {source_ip} : {line}", flush=True)
    try:
        with open(LOG_FILE, "a") as journal:
            journal.write(line + "\n")
    except OSError as err:
        print(f"[warn] journal non écrit : {err}", flush=True)
    update_registry(source_ip, payload, registry)


# --- Registre en mémoire (réhydraté depuis le JSONL au démarrage) ---------

def update_registry(source_ip, payload, registry):
    """
    Mise à jour du suivi : une ligne par éolienne.

    Clef de ligne = hostname exfiltré si le payload en fournit un, sinon
    l'IP source (beacons malformés). Même si toutes les connexions partagent
    une même IP de sortie (bridge QubesOS, NAT...), chaque éolienne garde
    sa ligne : compteur, last/first et état 🟢/🔴 par turbine.
    """
    now = time.time()
    if isinstance(payload, dict) and payload.get("host"):
        key = str(payload["host"])
        hostname = key
    else:
        key = source_ip
        hostname = "?"
    slot = registry.setdefault(key, {
        "hostname": hostname, "ip": source_ip, "first": now,
        "last": now, "count": 0, "peers": [],
    })
    if isinstance(payload, dict) and payload.get("host"):
        slot["hostname"] = hostname
    slot["ip"] = source_ip   # dernière IP source vue (débug du routage)
    slot["last"] = now
    slot["count"] += 1
    if isinstance(payload, dict) and isinstance(payload.get("peers"), dict):
        # mouvement latéral : résumé du dernier balayage inter-éoliennes
        slot["peers"] = [
            f"{peer} ({data.get('ip', '?')})"
            for peer, data in sorted(payload["peers"].items())
        ]


def load_registry(path):
    """Rejoue l'historique JSONL pour pré-remplir la table après un restart."""
    registry = {}
    try:
        with open(path) as journal:
            for line in journal:
                try:
                    entry = json.loads(line)
                    update_registry(
                        entry.get("src_ip", "?"),
                        entry.get("payload", {}),
                        registry,
                    )
                except (ValueError, TypeError):
                    continue
    except OSError:
        pass
    return registry


# --- Vue HTML -------------------------------------------------------------

PAGE_STYLE = """
<style>
    body { font-family: monospace; margin: 2em; }
    table { border-collapse: collapse; }
    td, th { border: 1px solid #888; padding: 4px 10px; text-align: left; }
    th { background: #222; color: #fff; }
    .ok { color: #080; font-weight: bold; }
    .ko { color: #c00; font-weight: bold; }
    .muted { color: #666; }
</style>
"""

LOGIN_PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<title>TurboElec C2</title>{style}</head>
<body>
<h2>TurboElec C2</h2>
<form method="POST" action="/login">
    <label>password</label>
    <input type="password" name="password" autofocus>
    <input type="submit" value="Login">
    {error}
</form>
</body></html>"""


def render_login(error=""):
    message = f'<p style="color:#c00">{html.escape(error)}</p>' if error else ""
    return LOGIN_PAGE.format(style=PAGE_STYLE, error=message)


def render_dashboard(registry):
    rows = ""
    for key in sorted(registry):
        slot = registry[key]
        silent = time.time() - slot["last"]
        state = (
            '<span class="ok">🟢 actif</span>'
            if silent <= SILENCE_THRESHOLD
            else '<span class="ko">🔴 silencieux</span>'
        )
        peers = slot["peers"]
        peers_cell = (
            "<br />".join(html.escape(peer) for peer in peers)
            if peers
            else '<span class="muted">—</span>'
        )
        rows += f"""<tr>
<td>{html.escape(str(slot["ip"]))}</td>
<td>{html.escape(slot["hostname"])}</td>
<td>{time.strftime("%H:%M:%S", time.localtime(slot["first"]))}</td>
<td>{time.strftime("%H:%M:%S", time.localtime(slot["last"]))}</td>
<td>{slot["count"]}</td>
<td>{peers_cell}</td>
<td>{state}</td>
</tr>"""
    title = time.strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="{REFRESH}">
<title>TurboElec C2 - beacons</title>{PAGE_STYLE}</head>
<body>
<h2>TurboElec C2 - beacons (maj {title})</h2>
<table>
<tr><th>IP</th><th>Hostname</th><th>Premier</th><th>Dernier</th>
    <th>Beacons</th><th>Dernier scan peers</th><th>État</th></tr>
{rows}
</table>
<p class="muted">🟢 actif : beacon &lt; {SILENCE_THRESHOLD} s ;
🔴 silencieux : au-delà — validation de l'exercice défensif.</p>
</body></html>"""


# --- Serveur HTTP ---------------------------------------------------------

class C2Handler(BaseHTTPRequestHandler):
    registry = {}   # partagé : rempli par les POST /beacon et le replay JSONL

    def do_POST(self):
        if self.path in ("/beacon", "/beacon/"):
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            try:
                payload = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                payload = {"raw": raw.decode("utf-8", errors="replace")}
            log_beacon(self.client_address[0], payload, self.registry)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{\"ok\":true}")
        elif self.path == "/login":
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            try:
                fields = parse_qs(body.decode())
            except (ValueError, UnicodeDecodeError):
                fields = {}
            supplied = fields.get("password", [""])[0]
            if hmac.compare_digest(supplied, C2_PASSWORD):
                cookie = f"{COOKIE}={SESSION_TOKEN}; Path=/; HttpOnly; SameSite=Strict"
                self.send_response(303)
                self.send_header("Set-Cookie", cookie)
                self.send_header("Location", "/")
                self.end_headers()
            else:
                self.show_login(error="mot de passe invalide")
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path in ("/probe", "/probe/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"C2 alive\n")
            return
        if self.path not in ("/", ""):
            self.send_response(404)
            self.end_headers()
            return
        # mire : cookie de session obligatoire
        if self.cookie_token() != SESSION_TOKEN:
            self.show_login()
            return
        body = render_dashboard(self.registry).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def show_login(self, error=""):
        body = render_login(error).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def cookie_token(self):
        raw = self.headers.get("Cookie", "")
        for pair in raw.split(";"):
            key, _, value = pair.strip().partition("=")
            if key == COOKIE:
                return value
        return ""

    def log_message(self, fmt, *args):
        # access log HTTP inutile : chaque beacon est déjà journalisé
        return


def main():
    C2Handler.registry = load_registry(LOG_FILE)
    slots = len(C2Handler.registry)
    print(
        f"Registre réhydraté : {slots} IP source(s) depuis {LOG_FILE}",
        flush=True,
    )
    server = ThreadingHTTPServer((LISTEN_ADDR, LISTEN_PORT), C2Handler)
    print(f"Serveur C2 démarré sur {LISTEN_ADDR}:{LISTEN_PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

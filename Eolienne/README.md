# Instance Docker

## Configuration
Les mots de passe sont configurable dans le fichier Dockerfile :
- mot de passe du compte operateur sur l'IHM (operator par défaut)
- mot de passe d'accès à l'automate Siemens (maint01 par défaut)

## Construction
1. Se déplacer dans le dossier `git_simics/Eolienne/`
2. Executer
```
$ docker build -t simics_eolienne .
```

## Lancement et récupération de l'adresse IP
### Linux
```
$ DOCKER_ID=$(docker run --rm --detach simics_eolienne)
$ docker inspect --format '{{ .NetworkSettings.IPAddress }}' $DOCKER_ID
```

### Windows

*Note : Docker Desktop for Windows ne permet pas l'exposition des ports. L'exemple suivant permet de lier le port du container avec celui de l'hôte*

```
cmd> for /f "delims=" %i in ('docker run --publish 80:80 --publish 502:502 --rm --detach simics_eolienne') do set DOCKER_ID=%i
cmd> docker inspect --format='{{.NetworkSettings.IPAddress}}' %DOCKER_ID%
```

## Services accessibles

```
$ nmap -n -p- --script=modbus-discover <EOLIENNE_IP>
Starting Nmap 7.95 ( https://nmap.org ) at 2026-10-15 16:09 CEST
Nmap scan report for A.B.C.D
Host is up (0.000090s latency).
Not shown: 65532 closed tcp ports (conn-refused)
PORT    STATE SERVICE
80/tcp  open  http
102/tcp open  iso-tsap
502/tcp open  modbus
| modbus-discover: 
|   sid 0x42: 
|     Slave ID data: HAXOM-SIMU-TURBOELEC-1.5.0\xFF
|_    Device identification: HAXOM SIMU-TURBOELEC 1.5.0

Nmap done: 1 IP address (1 host up) scanned in 1.42 seconds
```

- IHM de supervision web [http://<EOLIENNE_IP/](http://<EOLIENNE_IP/) (**l'accès est en HTTP et non HTTPS**)

![IHM de superivison](IHM_eolienne.png)

## Maintenance de l'application

Les services sont supervisés par `supervisord`, qui relance automatiquement tout process qui meurt — pratique en démo pour montrer un service tombé et relancé.

```
# État de tous les services de la simulation
$ docker exec $DOCKER_ID supervisorctl status

# Logs d'un service (ex. le serveur Modbus)
$ docker exec $DOCKER_ID tail -f /tmp/eolienne_server.log

# Relancer / arrêter un service
$ docker exec $DOCKER_ID supervisorctl restart eolienne_process
```

## Dépendances Python

Les versions de `pymodbus` et `python-snap7` sont figées dans `requirements.txt`
(plus dans le Dockerfile) et installées dans le venv `/data/venv` lors du
`docker build` : modifier ce fichier et relancer le build suffit pour changer de
version.

## Arborescence

```
Eolienne/
├── Dockerfile                  # image de la simulation (mots de passe configurables)
├── requirements.txt            # dépendances Python (pymodbus, python-snap7)
├── supervisord.conf            # supervision / relance auto des 7 services
├── IHM_eolienne.png            # capture d'écran de l'IHM
├── process/
│   ├── elevator_common.py      # schéma DB1 ascenseur + helpers partagés (fichier central)
│   ├── wind.py                 # simulateur de vent (rafales), écrit /tmp/wind.txt
│   ├── eolienne_server.py      # serveur Modbus TCP (port 502)
│   ├── eolienne_process.py     # logique de contrôle de l'éolienne
│   ├── ascenseur_server.py     # automate S7comm protégé (port 102) + simu physique
│   ├── ascenseur_process.py    # interlock éolienne / ascenseur
│   └── ascenseur_api.py        # API REST ascenseur (port 8080, loopback)
└── web/                        # IHM PHP (index.php, pics/, phpmodbus/ versionné)
```

Pour toute évolution de la DB1 de l'ascenseur, modifier en premier
`process/elevator_common.py` : les trois process (serveur, interlock et API)
partagent ce schéma via ce module unique.

## Suppression
```
$ docker rmi simics_eolienne
```

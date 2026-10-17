# Serveur C2 (formation)

Collecteur de beacons pour la partie « malware » de l'exercice : le
conteneur `turboelec_c2` reçoit les connexions de télémétrie déguisée
embarquées dans les éoliennes.

## Construction
```
$ docker build -t turboelec_c2 .
```

## Lancement
```
$ docker run --rm --detach --name turboelec_c2 turboelec_c2
```
Sur un réseau user-defined (recommandé, résolution DNS inter-conteneurs) :
```
$ docker run --rm --detach --name turboelec_c2 --network <nom_du_reseau> turboelec_c2
```

## Suivi des beacons

Vue web formateur (mire mot de passe, auto-refresh 10 s) :

```
http://<C2_IP>:4444/
```

Malware côté éolienne : le beacon de scan part à chaque cycle (90 s),
même si aucun peer n'a répondu — un `peers` vide est le signal explicite
« le balayage est bloqué » au C2.

La table donne une ligne par éolienne (clef = hostname exfiltré, repli
sur l'IP source pour les beacons sans payload exploitable) : hostname,
dernière IP source vue, premier/dernier beacon, nombre de beacons,
résumé du dernier balayage Modbus des autres éoliennes (mouvement
latéral) et état — 🟢 actif (beacon < 60 s) / 🔴 silencieux : l'absence
de nouveau beacon pour une éolienne donnée valide le blocage par son
pare-feu local, même si toutes les connexions partagent une même IP de
sortie (bridge QubesOS, NAT...).

Colonne « Dernier scan peers » :
- `—` : aucun balayage reçu pour cette éolienne ;
- liste : voisins vus au dernier balayage (trafic sortant 502 OK) ;
- 🔒 « aucun peer détecté — blocage sortant 502 ? » : le dernier
  balayage n'a vu personne — validation immédiate de l'efficacité du
  blocage Modbus par le stagiaire, sans attendre l'analyse PCAP.

Mot de passe par défaut : **`Ev1l_W3atherSyn4c`** (nom d'« outil
attaquant », clin d'œil au camouflage `weather_sync` du malware). Pour
le changer :

- au build : `docker build --build-arg C2_PASSWORD=... -t turboelec_c2 .`
- à l'exécution : `environment: C2_PASSWORD: ...` sur le service `c2`
  du docker-compose racine (prioritaire sur la valeur de l'image) ;
- dans le code : `C2_PASSWORD` en tête de `c2_server.py` (run hors Docker).

Le `POST /beacon` n'est pas authentifié : le malware ne doit pas connaître
le secret, il doit rester détectable/bloquable par les stagiaires. La sonde
`GET /probe` (« C2 alive ») est également ouverte, sans donnée.

Journal en ligne de commande :

```
$ docker logs -f turboelec_c2
$ docker exec turboelec_c2 cat /data/c2_beacons.jsonl
```
Chaque beacon journalise l'IP source, le hostname et les données exfiltrées.
L'historique est rechargé au démarrage du C2 : la vue web survit à un
restart du conteneur (sessions ouvertes exceptées, volontairement).

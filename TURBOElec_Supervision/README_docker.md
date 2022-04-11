# Instance Docker

## Construction
1. Se déplacer dans le dossier $git_simics$/TURBOElec_Supervision
2. Executer
```
$ docker build -t simics_turboelec_supervision .
```

## Lancement automatique

Le fichier launch.sh lance automatique des éolionnes ainsi que la supervision de ces dernières. Les adresses IP des différents composants sont affichées automatiquement (le nombre d'éolionnes est configurable dans ce même fichier, via la variable NB_EOL).
```
$ ./launch.sh
```

## Lancement manuel
Les adresses IP des éoliennes sont transmises par la variable d'environnement $EOL_IP sous la forme suivante :
```
export EOL_IP=<IP Eolienne 1>;<IP Eolienne 2>;IP Eolienne 3>...
```

```
$ DOCKER_ID=$(docker run --rm -e EOL_IP=$EOL_IP --detach -v /tmp/usineeol/:/tmp/usineeol/:ro simics_turboelec_supervision)
$ docker inspect --format '{{ .NetworkSettings.IPAddress }}' $DOCKER_ID
```

## Suppression
```
$ docker rmi simics_turboelec_supervision
```

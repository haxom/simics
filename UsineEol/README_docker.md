# Instance Docker

## Construction
1. Se déplacer dans le dossier $git_simics$/UsineEol/
2. Executer
```
$ docker build -t simics_usineeol .
```

## Lancement et récupération de l'adresse IP
Les adresses IP des éoliennes sont transmises par la variable d'environnement $EOL_IP sous la forme suivante :
```
export EOL_IP=<IP Eolienne 1>;<IP Eolienne 2>;IP Eolienne 3>...
```

```
$ DOCKER_ID=$(docker run --rm -e EOL_IP=$EOL_IP --detach -v /tmp/usineeol/:/tmp/usineeol/:ro simics_usineeol)
$ docker inspect --format '{{ .NetworkSettings.IPAddress }}' $DOCKER_ID
```

## Suppression
```
$ docker rmi simics_usineeol
```

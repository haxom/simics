# Instance Docker

## Construction
1. Se déplacer dans le dossier $git_simics$/Eolienne/
2. Executer
```
$ docker build -t simics_eolienne .
```

## Lancement et récupération de l'adresse IP
```
$ DOCKER_ID=$(docker run --rm --detach simics_eolienne)
$ docker inspect --format '{{ .NetworkSettings.IPAddress }}' $DOCKER_ID
```

## Suppression
```
$ docker rmi simics_eolienne
```

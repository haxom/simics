# Instance Docker

## Construction
1. Se déplacer dans le dossier $git_simics$/Portail/
2. Executer
```
$ docker build -t simics_portail .
```

## Lancement et récupération de l'adresse IP
### Linux
```
$ DOCKER_ID=$(docker run --rm --detach simics_portail)
$ docker inspect --format '{{ .NetworkSettings.IPAddress }}' $DOCKER_ID
```

### Windows

*Note : Docker Desktop for Windows ne permet pas l'exposition des ports. L'exemple suivant permet de lier le port du container avec celui de l'hôte*

```
cmd> for /f "delims=" %i in ('docker run --publish 80:80 --publish 502:502 --rm --detach simics_portail') do set DOCKER_ID=%i
cmd> docker inspect --format='{{.NetworkSettings.IPAddress}}' %DOCKER_ID%
```

## Suppression
```
$ docker rmi simics_portail
```

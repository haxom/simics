# Instance Docker

## Configuration
Le mot de passe du compte "operator" ("operator" par défaut) peut être configuré dans le fichier Dockerfile, à la ligne :
```
RUN echo SetEnv OPERATOR_PWD operator >> /etc/apache2/conf-enabled/environment.conf
```

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

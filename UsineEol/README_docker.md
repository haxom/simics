# Instance Docker

## Construction
1. Se déplacer dans le dossier $git_simics$/UsineEol/
2. Executer
```
$ docker build -t simics_usineeol .
```

## Lancement et récupération de l'adresse IP
Un fichier eoliennes.txt doit être créé et contenir la liste des adresses IP des éoliennes sous la forme suivante :
```
<IP Eolienne 1>;<IP Eolienne 2>;IP Eolienne 3>...
```

Le dossier contenant ce fichier devra être partagé avec le container UsineEol, par exemple en le plaçant dans le dossier hôte /tmp/usineeol/.

```
$ DOCKER_ID=$(docker run --rm --detach -v /tmp/usineeol/:/tmp/usineeol/:ro simics_usineeol)
$ docker inspect --format '{{ .NetworkSettings.IPAddress }}' $DOCKER_ID
```

## Suppression
```
$ docker rmi simics_usineeol
```

# SIMICS
## Introduction
Ce dépôt GIT contient un ensemble de projets de simulations de processus industriels.

Les différents projets sont indépendants les uns des autres, même s'ils ont des bases communes :
 * Un script de simulation du processus industriel, codé en Python
 * Une base de registres (coil / registers) accessibles avec le protocole ModBus
 * Une IHM représentant le processus et permettant des actions simples (état de capteur, actionneurs, etc.), codée en PHP
 * Un constructeur pour Docker (Dockerfile) pour chaque élément (pas systématique)
 * Une configuration I/O avec les GPIO du Raspberry PI (pas systématique) et des équipements électroniques (moteurs, LED, capteurs, etc.)
 * Des modèles d'impression pour imprimante 3D (pas systématique)

## Dépendances
 * [pymodbys](https://github.com/riptideio/pymodbus)
```
$ pip install pymodbus --user
```
 * [RPi.GPIO](https://sourceforge.net/projects/raspberry-gpio-python/) : required for the use of Raspberry PI's GPIO
```
$ pip install RPi.GPIO --user
```

 * [PhpModbus](https://github.com/krakorj/phpmodbus/) : required for web HMI
```
already included in the projects
```

## Done

 * Processus d'un portail électrique
 * Processus d'une éolienne

## Ongoing / Todo

 * Système simplifié d'une centrale nucléaire


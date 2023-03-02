# SIMICS
## Introduction
Ce dépôt GIT contient un ensemble de projets de simulations de processus industriels.

Les différents projets sont indépendants les uns des autres, même s'ils ont des bases communes :
 * Un script de simulation du processus industriel, codé en Python
 * Une base de registres (coil / registers) accessibles avec le protocole ModBus
 * Une IHM représentant le processus et permettant des actions simples (état de capteur, actionneurs, etc.), codée en PHP
 * Un constructeur pour Docker (Dockerfile) pour chaque élément

## Installation

```
$ git clone https://github.com/haxom/simics
$ cd simics
$ git submodule update --init
```

## Done

 * Processus d'un portail électrique
 * Processus d'une éolienne

## Ongoing / Todo

 * Système simplifié d'une centrale nucléaire


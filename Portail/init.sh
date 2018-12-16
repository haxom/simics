#!/bin/sh
### BEGIN INIT INFO
# Provides:          Nom du script
# Required-Start:    $local_fs $network
# Required-Stop:     $local_fs
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Description courte
# Description:       Description longue
### END INIT INFO

echo 0 > web/hauteur.txt
socat TCP-LISTEN:502,fork TCP:127.0.0.1:5002

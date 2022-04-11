#!/bin/bash

export NB_EOL=5

# Stop Supervisor
echo "Arrêt de la supervision en cours..."
for cont in $(docker ps | grep simics_turboelec_supervision | cut -d' ' -f1);
do
	OUTPUT=$(docker stop ${cont});
done

# Stop all Eoliennes
echo "Arrêt des eoliennes en cours..."
for cont in $(docker ps | grep simics_eolienne | cut -d' ' -f1);
do
	OUTPUT=$(docker stop ${cont});
done

# Run new Eoliennes
export EOL_IP=""
echo ""
echo "********************************"
echo "Démarrage de ${NB_EOL} éoliennes"
for run in $(seq ${NB_EOL});
do
	DOCKER_ID=$(docker run --rm --detach simics_eolienne)
	IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' ${DOCKER_ID})
	echo "Eolienne ${run} : ${IP}"
	EOL_IP="${EOL_IP}${IP};"
done
echo "********************************"

# Launch Supervisor
echo ""
echo "********************************"
echo "Démarrage de la supervision"
DOCKER_ID=$(docker run --rm -e EOL_IP=${EOL_IP::-1} --detach -v /tmp/usineeol/:/tmp/usineeol/:ro simics_turboelec_supervision)
SUP_IP=$(docker inspect --format '{{ .NetworkSettings.IPAddress }}' $DOCKER_ID)
echo "Supervision : ${SUP_IP}"
echo "********************************"

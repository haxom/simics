FROM debian:trixie
ENV TERM linux
RUN apt-get update && apt-get -y upgrade && apt-get -y install python3

# Mot de passe de la mire web formateur (vue http://<C2>:4444/).
# Override au build : docker build --build-arg C2_PASSWORD=... .
# Override au runtime : C2_PASSWORD dans le .env du lab (le compose
# passe la variable au conteneur, elle prime sur la valeur de l'image).
ARG C2_PASSWORD=Ev1l_W3atherSyn4c
ENV C2_PASSWORD=${C2_PASSWORD}

COPY c2_server.py /data/c2_server.py
WORKDIR /data

EXPOSE 4444/tcp

# Serveur C2 de la formation (collecte des beacons des éoliennes infectées)
CMD ["python3", "/data/c2_server.py"]

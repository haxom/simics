FROM debian:trixie
ENV TERM linux
RUN apt-get update && apt-get -y upgrade && apt-get -y install dialog apt-utils
RUN apt-get -y install python3 python3-venv apache2 php libapache2-mod-php supervisor iptables tcpdump

# Python : venv dans /data + dépendances figées dans requirements.txt
ENV VIRTUAL_ENV=/data/venv
ENV PATH="/data/venv/bin:$PATH"
COPY requirements.txt /data/requirements.txt
RUN python3 -m venv $VIRTUAL_ENV
RUN pip install -r /data/requirements.txt

COPY . /data
WORKDIR /data

# Déploiement du site : uniquement les fichiers utiles.
# (le dépôt web/phpmodbus embarque son .git, ses tests, examples et
#  tutorials : ils ne doivent pas être servis par Apache.)
RUN rm -f /var/www/html/index.html \
 && mkdir /var/www/html/phpmodbus \
 && cp /data/web/index.php /var/www/html/ \
 && cp /data/web/firewall.php /var/www/html/ \
 && cp -r /data/web/pics /var/www/html/pics \
 && cp -r /data/web/phpmodbus/Phpmodbus /var/www/html/phpmodbus/Phpmodbus \
 && cp /data/web/phpmodbus/license.txt /var/www/html/phpmodbus/license.txt \
 && chown -R www-data:www-data /var/www/html

RUN echo SetEnv OPERATOR_PWD operator >> /etc/apache2/conf-enabled/environment.conf

ENV S7_PASSWORD maint01

EXPOSE 80/tcp
EXPOSE 102/tcp
EXPOSE 502/tcp

# Tous les services sont supervisés par supervisord (relance automatique).
# État des services : docker exec <conteneur> supervisorctl status
CMD ["/usr/bin/supervisord", "-n", "-c", "/data/supervisord.conf"]

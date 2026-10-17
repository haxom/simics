FROM debian:trixie
ENV TERM linux
RUN apt-get update && apt-get -y upgrade && apt-get -y install dialog apt-utils
RUN apt-get -y install python3 python3-venv apache2 php libapache2-mod-php supervisor

# Python : venv dans /data + dépendances figées dans requirements.txt
# (même pattern que l'éolienne : plus de pip --user/--break-system-packages)
ENV VIRTUAL_ENV=/data/venv
ENV PATH="/data/venv/bin:$PATH"
COPY requirements.txt /data/requirements.txt
RUN python3 -m venv $VIRTUAL_ENV
RUN pip install -r /data/requirements.txt

COPY . /data
WORKDIR /data

# ServerName : évite le warning AH00558 d'apache2
RUN echo 'ServerName localhost' > /etc/apache2/conf-available/servername.conf \
 && ln -s /etc/apache2/conf-available/servername.conf /etc/apache2/conf-enabled/

# Déploiement du site : uniquement les fichiers utiles.
# (le dépôt web/phpmodbus embarque son .git, ses tests, examples et
#  tutorials : ils ne doivent pas être servis par Apache.)
RUN rm -f /var/www/html/index.html \
 && cp /data/web/index.php /data/web/modbusactions.php /var/www/html/ \
 && cp /data/web/hauteur.txt /var/www/html/ \
 && cp /data/web/*.jpg /data/web/*.png /data/web/*.gif /var/www/html/ \
 && cp -r /data/web/css /var/www/html/css \
 && mkdir /var/www/html/phpmodbus \
 && cp -r /data/web/phpmodbus/Phpmodbus /var/www/html/phpmodbus/Phpmodbus \
 && cp /data/web/phpmodbus/license.txt /var/www/html/phpmodbus/license.txt \
 && chmod 664 /var/www/html/hauteur.txt \
 && chown -R www-data:www-data /var/www/html

EXPOSE 80/tcp
EXPOSE 502/tcp

# Tous les services sont supervisés par supervisord (relance automatique,
# comme l'éolienne). État : docker exec <conteneur> supervisorctl status
CMD ["/usr/bin/supervisord", "-n", "-c", "/data/supervisord.conf"]

FROM debian:trixie
ENV TERM linux
RUN apt-get update && apt-get -y upgrade && apt-get -y install dialog apt-utils
RUN apt-get -y install python3 python3-pip apache2 php libapache2-mod-php
RUN pip3 install pymodbus==3.12.1 python-snap7==3.2.1 --user --break-system-packages
COPY . /data
WORKDIR /data
RUN cp -r /data/web/* /var/www/html && chown -R www-data:www-data /var/www/html/ && rm /var/www/html/index.html

RUN echo SetEnv OPERATOR_PWD operator >> /etc/apache2/conf-enabled/environment.conf

ENV S7_PASSWORD maint01

EXPOSE 80/tcp
EXPOSE 102/tcp
EXPOSE 502/tcp

CMD service apache2 restart & python3 /data/process/wind.py > /tmp/wind.log 2>&1 & sleep 5 && python3 /data/process/eolienne_server.py > /tmp/eolienne_server.log 2>&1 & sleep 10 && python3 /data/process/ascenseur_server.py > /tmp/ascenseur_server.log 2>&1 & python3 /data/process/eolienne_process.py > /tmp/eolienne_process.log 2>&1 & python3 /data/process/ascenseur_process.py > /tmp/ascenseur_process.log 2>&1 & python3 /data/process/ascenseur_api.py > /tmp/ascenseur_api.log 2>&1 & tail -f /dev/null

FROM debian
ENV TERM linux
RUN apt-get update && apt-get -y upgrade && apt-get -y dist-upgrade && apt-get -y install dialog apt-utils
RUN apt-get -y install git apache2 php libapache2-mod-php vim
RUN apt-get -y install python3 python3-opcua python3-pymodbus
COPY . /data
WORKDIR /data
RUN cp -r /data/web/* /var/www/html && chown -R www-data:www-data /var/www/html/ && rm /var/www/html/index.html

EXPOSE 80/tcp
EXPOSE 4840/tcp

CMD echo $EOL_IP > /tmp/eoliennes.txt && service apache2 restart && python3 /data/opcua/server_opcua.py && tail -f /dev/null

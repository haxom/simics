FROM debian
ENV TERM linux
RUN apt-get update && apt-get -y upgrade && apt-get -y dist-upgrade && apt-get -y install dialog apt-utils
RUN apt-get -y install git apache2 php libapache2-mod-php vim
COPY . /data
WORKDIR /data
RUN cp -r /data/web/* /var/www/html && chown -R www-data:www-data /var/www/html/ && rm /var/www/html/index.html

EXPOSE 80/tcp

CMD echo $EOL_IP > /tmp/eoliennes.txt && service apache2 restart && tail -f /dev/null

FROM debian
WORKDIR /root
ENV TERM linux
RUN apt-get update && apt-get -y upgrade && apt-get -y dist-upgrade && apt-get -y install dialog apt-utils
RUN apt-get -y install git apache2 php7.0 libapache2-mod-php7.0 vim
RUN git clone https://github.com/haxom/simics && cp -r /root/simics/UsineEol/web/* /var/www/html && chown -R www-data:www-data /var/www/html/ && rm /var/www/html/index.html

EXPOSE 80/tcp

CMD service apache2 restart && tail -f /dev/null

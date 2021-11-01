FROM debian
WORKDIR /root
ENV TERM linux
RUN apt-get update && apt-get -y upgrade && apt-get -y dist-upgrade && apt-get -y install dialog apt-utils
RUN apt-get -y install python3 python3-pip git apache2 php libapache2-mod-php vim
RUN pip install pymodbus --user
RUN git clone https://github.com/haxom/simics && cp -r /root/simics/Eolienne/web/* /var/www/html && chown -R www-data:www-data /var/www/html/ && rm /var/www/html/index.html

EXPOSE 80/tcp
EXPOSE 502/tcp

CMD service apache2 restart && python /root/simics/Eolienne/process/eolienne_server.py &> /dev/null & python /root/simics/Eolienne/process/eolienne_process.py &> /dev/null & tail -f /dev/null

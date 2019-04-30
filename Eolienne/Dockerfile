FROM debian
WORKDIR /root
ENV TERM linux
RUN apt-get update && apt-get -y upgrade && apt-get -y dist-upgrade && apt-get -y install dialog apt-utils
RUN apt-get -y install python python-pip git apache2 php7.0 libapache2-mod-php7.0 vim socat
RUN pip install pymodbus --user
RUN git clone https://github.com/haxom/simics && cp -r /root/simics/Eolienne/web/* /var/www/html && chown -R www-data:www-data /var/www/html/ && rm /var/www/html/index.html && chmod +x /root/simics/Eolienne/init_socat.sh
RUN echo 'python /root/simics/Eolienne/process/eolienne_server.py &' > /root/run.sh && echo 'python /root/simics/Eolienne/process/eolienne_process.py &' >> /root/run.sh && chmod +x /root/run.sh

EXPOSE 80/tcp
EXPOSE 502/tcp

CMD service apache2 restart && python /root/simics/Eolienne/process/eolienne_server.py &> /dev/null & python /root/simics/Eolienne/process/eolienne_process.py &> /dev/null & /root/simics/Eolienne/init_socat.sh

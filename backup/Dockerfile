FROM postgis/postgis:18-3.6-alpine

COPY mc /usr/local/bin/mc

RUN mkdir -p /backups && chmod 700 /backups

COPY scripts/ /scripts/
RUN chmod 700 /scripts/*.sh

COPY crontab /etc/crontabs/root

CMD ["crond", "-f", "-l", "8"]

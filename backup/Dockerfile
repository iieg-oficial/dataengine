FROM postgis/postgis:18-3.6-alpine

RUN apk add --no-cache rclone age

RUN mkdir -p /backups && chmod 700 /backups

COPY scripts/ /scripts/
RUN chmod 700 /scripts/*.sh

COPY crontab /etc/crontabs/root

CMD ["crond", "-f", "-l", "8"]

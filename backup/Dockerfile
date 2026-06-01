FROM postgis/postgis:18-3.6-alpine

RUN apk add --no-cache curl && \
    curl -fsSL -o /usr/local/bin/mc https://dl.min.io/client/mc/release/linux-amd64/mc && \
    chmod +x /usr/local/bin/mc

RUN mkdir -p /backups && chmod 700 /backups

COPY scripts/ /scripts/
RUN chmod 700 /scripts/*.sh

COPY crontab /etc/crontabs/root

CMD ["crond", "-f", "-l", "8"]

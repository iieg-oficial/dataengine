FROM postgis/postgis:18-3.6-alpine

RUN apk add --no-cache curl \
    && curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc \
    && chmod +x /usr/local/bin/mc \
    && curl -fsSL https://github.com/aptible/supercronic/releases/download/v0.2.33/supercronic-linux-amd64 -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic

COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

COPY crontab /etc/supercronic/crontab

CMD ["supercronic", "/etc/supercronic/crontab"]

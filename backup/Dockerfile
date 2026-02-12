FROM postgres:18-alpine

RUN apk add --no-cache curl \
    && curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc \
    && chmod +x /usr/local/bin/mc

COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

COPY crontab /etc/crontabs/root

CMD ["crond", "-f", "-l", "2"]

FROM postgres:18.2-alpine

RUN apk add --no-cache dcron curl \
    && curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc \
    && chmod +x /usr/local/bin/mc

COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

COPY crontab /etc/crontabs/root

CMD ["crond", "-f", "-l", "2"]

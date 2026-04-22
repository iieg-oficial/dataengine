FROM python:3.13-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends cron \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh \
    && cp /app/crontab /etc/cron.d/jobs \
    && chmod 0644 /etc/cron.d/jobs \
    && touch /var/log/cron.log

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["cron", "-f"]

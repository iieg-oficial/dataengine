#!/bin/sh
alembic -c /app/alembic/mapalab_card/alembic.ini upgrade head
exec "$@"

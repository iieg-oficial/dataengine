-include .env
export

PROJECT_DIR := $(shell pwd)
CRON_JOB = $(cron_minute) $(cron_hour) * * * cd $(PROJECT_DIR) && make card >> $(PROJECT_DIR)/logs/cron_card.log 2>&1

.PHONY: help up down restart ps logs logs-primary logs-backup \
        shell backup restore clean build certs \
        cron-install cron-remove card \
        fw-status fw-setup fw-reset

help:
	@echo ""
	@echo "  up              Levantar todos los servicios"
	@echo "  down            Detener todos los servicios"
	@echo "  restart         Reiniciar todos los servicios"
	@echo "  build           Reconstruir imagenes (backup)"
	@echo "  ps              Estado de los contenedores"
	@echo ""
	@echo "  logs            Logs de todos los servicios"
	@echo "  logs-primary    Logs del primary"
	@echo "  logs-backup     Logs del backup"
	@echo ""
	@echo "  shell           Consola psql en primary"
	@echo ""
	@echo "  backup          Ejecutar respaldo manual"
	@echo "  restore         Restaurar dump (auto-detecta si solo hay un archivo)"
	@echo ""
	@echo "  certs           Generar certificados SSL (solo primera vez)"
	@echo "  clean           Eliminar volumenes (DESTRUCTIVO)"
	@echo ""
	@echo "  card            Ingesta tarjetas desde csv track card capa"
	@echo ""
	@echo "  cron-install    Instalar cron job diario para make card"
	@echo "  cron-remove     Remover cron job de ingesta"
	@echo ""

certs:
	@if [ -f postgres/certs/server.crt ] && [ -f postgres/certs/server.key ] && [ -f postgres/certs/ca.crt ]; then \
		echo "Certificados SSL ya existen, omitiendo generacion."; \
	else \
		echo "Generando certificados SSL..."; \
		mkdir -p postgres/certs; \
		openssl req -new -x509 -days 3650 -nodes \
			-keyout postgres/certs/ca.key \
			-out postgres/certs/ca.crt \
			-subj "/CN=dataengine-ca"; \
		openssl req -new -nodes \
			-keyout postgres/certs/server.key \
			-out postgres/certs/server.csr \
			-subj "/CN=postgres-primary"; \
		openssl x509 -req -days 730 \
			-in postgres/certs/server.csr \
			-CA postgres/certs/ca.crt \
			-CAkey postgres/certs/ca.key \
			-CAcreateserial \
			-out postgres/certs/server.crt; \
		rm -f postgres/certs/server.csr postgres/certs/ca.srl; \
		chmod 600 postgres/certs/ca.key postgres/certs/server.key; \
		chmod 644 postgres/certs/ca.crt postgres/certs/server.crt; \
		echo "Certificados SSL generados en postgres/certs/"; \
	fi

up: certs
	docker compose up -d
	@$(MAKE) cron-install

down:
	docker compose down

restart:
	docker compose down
	docker compose up -d
	@$(MAKE) cron-install

build:
	docker compose build --no-cache

ps:
	docker compose ps

logs:
	docker compose logs -f --tail=100

logs-primary:
	docker compose logs -f --tail=100 postgres-primary

logs-backup:
	docker compose logs -f --tail=100 pg-backup

shell:
	docker compose exec postgres-primary psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

backup:
	@DEBUG=$(DEBUG) bash backup/do-backup.sh

restore:
	@DEBUG=$(DEBUG) bash restore/do-restore.sh $(FILE)

restore-local:
	@PGHOST=$(MAPALAB_CARD_DB_HOST) PGPORT=$(MAPALAB_CARD_DB_PORT) \
	 PGUSER=$(MAPALAB_CARD_DB_USER) PGPASSWORD=$(MAPALAB_CARD_DB_PASSWORD) \
	 PGDATABASE=$(MAPALAB_CARD_DB_NAME) \
	 bash restore/do-restore-local.sh $(FILE)

clean:
	@echo "ATENCION: Esto eliminara todos los datos de PostgreSQL y backups"
	@read -p "Escribir 'si' para confirmar: " confirm && [ "$$confirm" = "si" ] || (echo "Cancelado" && exit 1)
	docker compose down -v

card:
	docker compose exec mapalab-card python run_bootstrap.py
cron-install:
	@mkdir -p $(PROJECT_DIR)/logs
	@( crontab -l 2>/dev/null | grep -v 'make card' | grep -v 'SHELL=/bin/bash' ; echo "SHELL=/bin/bash" ; echo "$(CRON_JOB)" ) | crontab -
	@echo "⏰ Cron job instalado: ingesta diaria a las $(cron_hour):$(cron_minute) con conda env etl (logs en logs/)"

cron-remove:
	@( crontab -l 2>/dev/null | grep -v 'make card' | grep -v 'SHELL=/bin/bash' ) | crontab - || true
	@echo "🛑 Cron job de ingesta removido"

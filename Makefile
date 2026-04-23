-include .env
export

PROJECT_DIR := $(shell pwd)
CRON_HOUR   = $(word 1,$(subst :, ,$(CRON_SCHEDULE)))
CRON_MINUTE = $(word 2,$(subst :, ,$(CRON_SCHEDULE)))
CRON_JOB    = $(CRON_MINUTE) $(CRON_HOUR) * * * cd $(PROJECT_DIR) && make card >> $(PROJECT_DIR)/logs/cron_card.log 2>&1

.PHONY: help up down restart ps logs logs-primary logs-backup logs-jobs \
        shell backup restore restore-local clean build certs \
        cron-install cron-remove \
        refresh-periodicity refresh-layer-tree refresh-layer-stats refresh-all \
        check-periodicity prod-migration

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
	@echo "  logs-jobs       Logs del cron en dataengine-jobs"
	@echo ""
	@echo "  shell           Consola psql en primary"
	@echo ""
	@echo "  backup          Ejecutar respaldo manual"
	@echo "  restore         Restaurar dump (auto-detecta si solo hay un archivo)"
	@echo ""
	@echo "  certs           Generar certificados SSL (solo primera vez)"
	@echo "  clean           Eliminar volumenes (DESTRUCTIVO)"
	@echo ""
	@echo "  prod-migration      Pull final Sheet + bootstrap v1.4.0 + seed + migrate + stamp"
	@echo "                      Ver: make prod-migration PROD_MIGRATION_FLAGS=\"--skip-etl\""
	@echo ""
	@echo "  refresh-periodicity Refrescar tabla de periodicidad (SQL)"
	@echo "  refresh-layer-tree  Refrescar cache del arbol de capas MapaLab"
	@echo "  refresh-layer-stats Refrescar stats (numeralia) del catalogo"
	@echo "  refresh-all         Ejecutar los tres refresh en orden"
	@echo "  check-periodicity   Verificar si periodicidad esta al dia"
	@echo ""
	@echo "  cron-install    Instalar cron job (solo ENV=production)"
	@echo "  cron-remove     Remover cron job"
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
ifeq ($(ENV),production)
	@DEBUG=$(DEBUG) bash backup/do-backup.sh
else
	@echo "⚠️  Backup deshabilitado en ENV=$(ENV). Solo disponible en production."
endif

restore:
	@DEBUG=$(DEBUG) bash restore/do-restore.sh $(FILE)

restore-local:
	@PGHOST=$(DATAENGINE_DB_HOST) PGPORT=$(DATAENGINE_DB_PORT) \
	 PGUSER=$(DATAENGINE_DB_USER) PGPASSWORD=$(DATAENGINE_DB_PASSWORD) \
	 PGDATABASE=$(DATAENGINE_DB_NAME) \
	 bash restore/do-restore-local.sh $(FILE)

clean:
	@echo "ATENCION: Esto eliminara todos los datos de PostgreSQL y backups"
	@read -p "Escribir 'si' para confirmar: " confirm && [ "$$confirm" = "si" ] || (echo "Cancelado" && exit 1)
	docker compose down -v

refresh-layer-tree:
	@echo "Refrescando arbol de capas..."
	@docker compose exec -T jobs python run_refresh_layer_tree.py
	@echo "OK"

refresh-layer-stats:
	@echo "Refrescando numeralia dinamica..."
	@docker compose exec -T jobs python run_refresh_layer_stats.py
	@echo "OK"

refresh-all: refresh-periodicity refresh-layer-tree refresh-layer-stats
	@echo "Todo refresh completado"

prod-migration:
	@./scripts/prod-migration.sh $(PROD_MIGRATION_FLAGS)

logs-jobs:
	@docker compose exec jobs tail -n 100 -f /var/log/cron.log

refresh-periodicity:
	@echo "Refrescando periodicidad..."
	@docker compose exec -T jobs python run_refresh_periodicity.py
	@echo "OK"

check-periodicity:
	@echo "Verificando periodicidad..."
	@docker compose exec -T postgres-primary psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) \
		-f /scripts/check_periodicity.sql -q
cron-install:
ifeq ($(ENV),production)
	@mkdir -p $(PROJECT_DIR)/logs
	@( crontab -l 2>/dev/null | grep -v 'make card' | grep -v 'SHELL=/bin/bash' ; echo "SHELL=/bin/bash" ; echo "$(CRON_JOB)" ) | crontab -
	@echo "⏰ Cron job instalado: ingesta diaria a las $(CRON_SCHEDULE) con conda env etl (logs en logs/)"
else
	@echo "⏰ Cron job omitido en ENV=$(ENV). Solo se instala en production."
endif

cron-remove:
	@( crontab -l 2>/dev/null | grep -v 'make card' | grep -v 'SHELL=/bin/bash' ) | crontab - || true
	@echo "🛑 Cron job de ingesta removido"

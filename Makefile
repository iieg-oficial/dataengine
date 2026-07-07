-include .env
export

PROJECT_DIR := $(shell pwd)
CRON_HOUR   = $(word 1,$(subst :, ,$(CRON_SCHEDULE)))
CRON_MINUTE = $(word 2,$(subst :, ,$(CRON_SCHEDULE)))
CRON_JOB    = $(CRON_MINUTE) $(CRON_HOUR) * * * cd $(PROJECT_DIR) && make card >> $(PROJECT_DIR)/logs/cron_card.log 2>&1

ESC      := $(shell printf '\033')
C_RESET  := $(ESC)[0m
C_BOLD   := $(ESC)[1m
C_DIM    := $(ESC)[2m
C_GREEN  := $(ESC)[32m
C_YELLOW := $(ESC)[33m
C_CYAN   := $(ESC)[36m

.PHONY: help up down restart ps logs logs-primary logs-backup logs-jobs \
        shell backup restore restore-local clean build certs \
        cron-install cron-remove \
        refresh-periodicity refresh-layer-tree refresh-layer-stats refresh-municipios refresh-all \
        check-periodicity prod-migration migrate migrate-status _migrate-report \
        ingest-metadata \
        version-json

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
	@echo "  prod-migration      Bootstrap idempotente + alembic upgrade head."
	@echo "                      Default: with-etl (pull del Sheet activo, fase de testing)."
	@echo "                      Override:  make prod-migration PROD_MIGRATION_FLAGS=\"--skip-etl\""
	@echo ""
	@echo "  migrate             Rebuild de imagen jobs + alembic upgrade head (muestra estado antes/despues)"
	@echo "  migrate-status      Estado de migraciones: resalta la actual y las pendientes (color)"
	@echo ""
	@echo "  refresh-periodicity Refrescar tabla de periodicidad (SQL)"
	@echo "  refresh-layer-tree  Refrescar cache del arbol de capas MapaLab"
	@echo "  refresh-layer-stats Refrescar stats (numeralia) del catalogo"
	@echo "  refresh-municipios  Refrescar MV mapalab.municipios desde mapa_base"
	@echo "  refresh-all         Ejecutar los tres refresh en orden"
	@echo "  check-periodicity   Verificar si periodicidad esta al dia"
	@echo ""
	@echo "  ingest-metadata     Ingesta upsert de metadatos a layer_metadata desde CSV."
	@echo "                      Uso: make ingest-metadata DEP=<dep> SOURCE=<path|url> [EXTRA=...]"
	@echo "                      EXTRA: --apply | --review --apply | --plan-out /tmp/plan.json"
	@echo "                      Sin --apply: dry-run (no toca DB). Sin DEP/SOURCE: imprime ayuda."
	@echo ""
	@echo "  cron-install    Instalar cron job (solo ENV=production)"
	@echo "  cron-remove     Remover cron job"
	@echo ""
	@echo "  version-json    Regenerar version-api/html/version.json desde VERSION"
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

up: certs version-json
	docker compose up -d
	@$(MAKE) cron-install

down:
	docker compose down

restart: version-json
	docker compose down
	docker compose up -d
	@$(MAKE) cron-install

version-json:
	@mkdir -p version-api/html
	@VERSION=$$(tr -d '[:space:]' < VERSION); \
	 SERVICE=$${SERVICE_NAME:-dataengine}; \
	 RELEASED_AT=$$(grep -m1 "^## \[$$VERSION\]" docs/CHANGELOG.md | sed -E 's/^## \[[^]]+\] - ([0-9-]+).*/\1/'); \
	 if [ -z "$$RELEASED_AT" ]; then echo "WARN: no se encontro entrada '## [$$VERSION] - YYYY-MM-DD' en docs/CHANGELOG.md" >&2; fi; \
	 printf '{"version":"%s","service":"%s","released_at":"%s"}\n' "$$VERSION" "$$SERVICE" "$$RELEASED_AT" > version-api/html/version.json; \
	 echo "version.json -> $$VERSION ($$SERVICE, $$RELEASED_AT)"

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

refresh-municipios:
	@echo "Refrescando mapalab.municipios (MV de IIEG + INEGI)..."
	@docker compose exec -T jobs python run_refresh_municipios.py
	@echo "OK"

refresh-all: refresh-periodicity refresh-layer-tree refresh-layer-stats refresh-municipios
	@echo "Todo refresh completado"

prod-migration:
	@./scripts/prod-migration.sh $(PROD_MIGRATION_FLAGS)

migrate:
	@printf "$(C_BOLD)» Sincronizando imagen de jobs con el repo...$(C_RESET)\n"
	@docker compose build jobs
	@docker compose up -d jobs
	@printf "\n$(C_BOLD)» Estado antes de migrar$(C_RESET)\n"
	@$(MAKE) --no-print-directory _migrate-report
	@printf "\n$(C_BOLD)» Aplicando migraciones alembic pendientes...$(C_RESET)\n"
	@docker compose exec -T jobs alembic upgrade head
	@printf "\n$(C_BOLD)» Estado despues de migrar$(C_RESET)\n"
	@$(MAKE) --no-print-directory _migrate-report
	@printf "$(C_GREEN)OK$(C_RESET)\n"

migrate-status:
	@printf "$(C_BOLD)» Estado de migraciones alembic$(C_RESET)\n"
	@$(MAKE) --no-print-directory _migrate-report

_migrate-report:
	@if ! err=$$(docker compose exec -T jobs true 2>&1 >/dev/null); then \
	  printf "  $(C_YELLOW)! No se pudo acceder al contenedor 'jobs'.$(C_RESET)\n"; \
	  reason=$$(printf '%s\n' "$$err" | grep -iE 'invalid spec|is not set|no such|not running|no configuration' | tail -1); \
	  if [ -n "$$reason" ]; then printf "  $(C_DIM)Motivo: %s$(C_RESET)\n" "$$reason"; fi; \
	  if printf '%s' "$$err" | grep -qiE 'invalid spec|is not set'; then \
	    printf "  $(C_DIM)Falta cargar el .env (variables vacias). Verifica que exista .env en este directorio.$(C_RESET)\n"; \
	  else \
	    printf "  $(C_DIM)Levantalo con 'make up' o 'make migrate'.$(C_RESET)\n"; \
	  fi; \
	else \
	  docker compose exec -T jobs alembic history --indicate-current 2>/dev/null | awk \
	  -v cur='$(C_CYAN)' -v pen='$(C_YELLOW)' -v app='$(C_DIM)' \
	  -v grn='$(C_GREEN)' -v bold='$(C_BOLD)' -v rst='$(C_RESET)' '\
	  { if ($$0 ~ /^[[:space:]]*$$/) next; \
	    n++; arr[n]=$$0; if (index($$0,"(current)")>0) curidx=n } \
	  END { \
	    if (n==0) { printf "  %s(sin historial de migraciones)%s\n", app, rst; exit } \
	    if (curidx==0) pend=n; else pend=curidx-1; \
	    if (pend==0) printf "  %s* Al dia%s -- %d migracion(es) aplicada(s), 0 pendientes\n\n", grn, rst, n; \
	    else printf "  %s* %d pendiente(s)%s de %d totales\n\n", pen, pend, rst, n; \
	    for (i=1;i<=n;i++) { \
	      if (curidx>0 && i==curidx) printf "  %s%s>%s %s%s  (actual)%s\n", cur, bold, rst, cur, arr[i], rst; \
	      else if (curidx==0 || i<curidx) printf "  %so %s  (pendiente)%s\n", pen, arr[i], rst; \
	      else printf "  %s+ %s%s\n", app, arr[i], rst; \
	    } \
	  }'; \
	fi

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

ingest-metadata:
	@if [ -z "$(DEP)" ] || [ -z "$(SOURCE)" ]; then \
		echo "Uso: make ingest-metadata DEP=<dependencia> SOURCE=<path|url> [EXTRA='--apply']"; \
		echo "Ejemplos:"; \
		echo "  make ingest-metadata DEP=sct SOURCE=/tmp/sct.csv"; \
		echo "  make ingest-metadata DEP=sct SOURCE=/tmp/sct.csv EXTRA=--apply"; \
		echo "  make ingest-metadata DEP=sct SOURCE=/tmp/sct.csv EXTRA='--review --apply'"; \
		echo "  make ingest-metadata DEP=sct SOURCE=/tmp/sct.csv EXTRA='--plan-out /tmp/plan.json'"; \
		exit 1; \
	fi
	@if echo "$(SOURCE)" | grep -qE "^https?://"; then \
		docker compose exec -T jobs python ingest/run_ingest_metadata.py \
			--dependencia "$(DEP)" --source "$(SOURCE)" $(EXTRA); \
	else \
		docker cp "$(SOURCE)" dataengine-jobs:/tmp/ingest_source.csv && \
		docker compose exec -T jobs python ingest/run_ingest_metadata.py \
			--dependencia "$(DEP)" --source /tmp/ingest_source.csv $(EXTRA); \
	fi

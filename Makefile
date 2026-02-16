-include .env
export

.PHONY: help up down restart ps logs logs-primary logs-replica logs-backup \
        shell shell-replica backup restore clean build certs

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
	@echo "  logs-replica    Logs de la replica"
	@echo "  logs-backup     Logs del backup"
	@echo ""
	@echo "  shell           Consola psql en primary"
	@echo "  shell-replica   Consola psql en replica (solo lectura)"
	@echo ""
	@echo "  backup          Ejecutar respaldo manual"
	@echo "  restore         Restaurar dump: make restore FILE=archivo.dump"
	@echo ""
	@echo "  certs           Generar certificados SSL (solo primera vez)"
	@echo "  clean           Eliminar volumenes (DESTRUCTIVO)"
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

down:
	docker compose down

restart:
	docker compose down
	docker compose up -d

build:
	docker compose build --no-cache

ps:
	docker compose ps

logs:
	docker compose logs -f --tail=100

logs-primary:
	docker compose logs -f --tail=100 postgres-primary

logs-replica:
	docker compose logs -f --tail=100 postgres-replica

logs-backup:
	docker compose logs -f --tail=100 pg-backup

shell:
	docker compose exec postgres-primary psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

shell-replica:
	docker compose exec postgres-replica psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

backup:
	docker compose exec pg-backup /scripts/backup.sh

restore:
ifndef FILE
	$(error Uso: make restore FILE=nombre_del_archivo)
endif
	@echo "$(FILE)" | grep -qE '(\.\.|/)' && { echo "Error: FILE no debe contener '..' ni '/'"; exit 1; } || true
	@[ "$$(basename '$(FILE)')" != "$(FILE)" ] && { echo "Error: FILE debe ser solo un nombre de archivo"; exit 1; } || true
	@docker compose exec -e PGPASSWORD=$(POSTGRES_PASSWORD) postgres-primary psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) \
		-c "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS postgis_topology;"
	@docker compose exec -e PGPASSWORD=$(POSTGRES_PASSWORD) postgres-primary sh -c '\
		HEADER=$$(head -c 5 /restore/$(FILE) | strings); \
		if echo "$$HEADER" | grep -q PGDMP; then \
			echo "Detectado: custom format"; \
			pg_restore -U $(POSTGRES_USER) -d $(POSTGRES_DB) \
				--no-owner \
				/restore/$(FILE) || true; \
		elif echo "$(FILE)" | grep -qE "\.gz$$"; then \
			echo "Detectado: sql comprimido"; \
			gunzip -c /restore/$(FILE) | psql -U $(POSTGRES_USER) -d $(POSTGRES_DB); \
		else \
			echo "Detectado: sql plano"; \
			psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -f /restore/$(FILE); \
		fi'
	@echo "Restauracion completada"

clean:
	@echo "ATENCION: Esto eliminara todos los datos de PostgreSQL y backups"
	@read -p "Escribir 'si' para confirmar: " confirm && [ "$$confirm" = "si" ] || (echo "Cancelado" && exit 1)
	docker compose down -v

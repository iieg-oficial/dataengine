-include .env
export

.PHONY: help up down restart ps logs logs-primary logs-replica logs-backup \
        shell shell-replica backup restore clean build

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
	@echo "  clean           Eliminar volumenes (DESTRUCTIVO)"
	@echo ""

up:
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
	@if echo "$(FILE)" | grep -qE '\.dump$$'; then \
		echo "Restaurando custom format: $(FILE)"; \
		docker compose exec postgres-primary pg_restore \
			-U $(POSTGRES_USER) -d $(POSTGRES_DB) \
			--clean --if-exists --no-owner \
			/restore/$(FILE); \
	elif echo "$(FILE)" | grep -qE '\.sql\.gz$$'; then \
		echo "Restaurando sql comprimido: $(FILE)"; \
		docker compose exec postgres-primary sh -c \
			"gunzip -c /restore/$(FILE) | psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)"; \
	elif echo "$(FILE)" | grep -qE '\.sql$$'; then \
		echo "Restaurando sql plano: $(FILE)"; \
		docker compose exec postgres-primary psql \
			-U $(POSTGRES_USER) -d $(POSTGRES_DB) \
			-f /restore/$(FILE); \
	else \
		echo "Formato no soportado. Usa .dump, .sql o .sql.gz"; \
		exit 1; \
	fi
	@echo "Restauracion completada"

clean:
	@echo "ATENCION: Esto eliminara todos los datos de PostgreSQL y backups"
	@read -p "Escribir 'si' para confirmar: " confirm && [ "$$confirm" = "si" ] || (echo "Cancelado" && exit 1)
	docker compose down -v

-include .env
export

FW_PORTS = 22 $(PG_PRIMARY_PORT) $(PG_REPLICA_PORT)

.PHONY: help up down restart ps logs logs-primary logs-replica logs-backup \
        shell shell-replica backup restore clean build certs \
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
	@echo "  logs-replica    Logs de la replica"
	@echo "  logs-backup     Logs del backup"
	@echo ""
	@echo "  shell           Consola psql en primary"
	@echo "  shell-replica   Consola psql en replica (solo lectura)"
	@echo ""
	@echo "  backup          Ejecutar respaldo manual"
	@echo "  restore         Restaurar dump (auto-detecta si solo hay un archivo)"
	@echo ""
	@echo "  certs           Generar certificados SSL (solo primera vez)"
	@echo "  clean           Eliminar volumenes (DESTRUCTIVO)"
	@echo ""
	@echo "  fw-status       Ver reglas actuales del firewall"
	@echo "  fw-setup        Aplicar reglas de firewall (usa ALLOWED_HOSTS)"
	@echo "  fw-reset        Resetear firewall (DESTRUCTIVO)"
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

up: certs fw-setup
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
	@bash restore/do-restore.sh $(FILE)

clean:
	@echo "ATENCION: Esto eliminara todos los datos de PostgreSQL y backups"
	@read -p "Escribir 'si' para confirmar: " confirm && [ "$$confirm" = "si" ] || (echo "Cancelado" && exit 1)
	docker compose down -v

fw-status:
	sudo ufw status numbered

fw-setup:
	@which ufw > /dev/null 2>&1 || { echo "Error: ufw no esta instalado. Ejecutar: sudo apt install ufw"; exit 1; }
	@test -n "$(ALLOWED_HOSTS)" || { echo "Error: ALLOWED_HOSTS no definida en .env"; exit 1; }
	@echo "Configurando firewall..."
	sudo ufw default deny incoming
	sudo ufw default allow outgoing
	@for host in $(ALLOWED_HOSTS); do \
		for port in $(FW_PORTS); do \
			echo "Permitiendo $$host -> puerto $$port/tcp"; \
			sudo ufw allow from $$host to any port $$port proto tcp 2>&1 || true; \
		done; \
	done
	sudo ufw --force enable
	@echo ""
	sudo ufw status numbered
	@echo "Firewall configurado."

fw-reset:
	@echo "ATENCION: Esto eliminara todas las reglas del firewall"
	@read -p "Escribir 'si' para confirmar: " confirm && [ "$$confirm" = "si" ] || { echo "Cancelado"; exit 1; }
	sudo ufw --force reset
	@echo "Firewall reseteado."

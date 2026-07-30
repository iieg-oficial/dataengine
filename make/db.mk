.PHONY: psql backup restore _certs

##@ Base de datos

psql: ## Consola psql en el primary
	@$(LIB)
	dc prod exec postgres-primary psql -U "$(POSTGRES_USER)" -d "$(POSTGRES_DB)"

backup: ## Respaldo manual, solo en produccion
	@$(LIB)
	banner 'BACKUP'
	require_production
	rule
	DEBUG=$(DEBUG) bash backup/do-backup.sh

restore: ## Restaurar un dump de restore/, con selector
	@$(LIB)
	banner 'RESTORE'
	rule
	DEBUG=$(DEBUG) bash restore/do-restore.sh

_certs:
	@$(LIB)
	if [ -f postgres/certs/server.crt ] && [ -f postgres/certs/server.key ] && [ -f postgres/certs/ca.crt ]; then
		exit 0
	fi
	mkdir -p postgres/certs
	openssl req -new -x509 -days 3650 -nodes \
		-keyout postgres/certs/ca.key \
		-out postgres/certs/ca.crt \
		-subj "/CN=dataengine-ca" 2>/dev/null
	openssl req -new -nodes \
		-keyout postgres/certs/server.key \
		-out postgres/certs/server.csr \
		-subj "/CN=postgres-primary" 2>/dev/null
	openssl x509 -req -days 730 \
		-in postgres/certs/server.csr \
		-CA postgres/certs/ca.crt \
		-CAkey postgres/certs/ca.key \
		-CAcreateserial \
		-out postgres/certs/server.crt 2>/dev/null
	rm -f postgres/certs/server.csr postgres/certs/ca.srl
	chmod 600 postgres/certs/ca.key postgres/certs/server.key
	chmod 644 postgres/certs/ca.crt postgres/certs/server.crt
	printf '  Certificados SSL generados en postgres/certs/\n'

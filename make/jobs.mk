.PHONY: refresh check-periodicity ingest-metadata

##@ Jobs

refresh: ## Refrescar caches y vistas, con selector
	@$(LIB)
	banner 'REFRESH'
	job=$$(pick 'Job' 'todos' $$REFRESH_ALL)
	rule
	if [ "$$job" = 'todos' ]; then
		for j in $$REFRESH_DEFAULT; do run_refresh "$$j"; done
	else
		run_refresh "$$job" forced
	fi
	rule
	printf '\n'

check-periodicity: ## Verificar si la periodicidad esta al dia
	@$(LIB)
	banner 'CHECK' 'periodicidad'
	rule
	dc prod exec -T postgres-primary psql -U "$(POSTGRES_USER)" -d "$(POSTGRES_DB)" \
		-f /scripts/check_periodicity.sql -q

ingest-metadata: ## Ingesta de metadatos a layer_metadata desde CSV o URL
	@$(LIB)
	banner 'INGEST' 'layer_metadata'
	rule
	ingest_metadata

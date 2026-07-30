.PHONY: migrate bootstrap

##@ Migraciones

migrate: ## Sincronizar imagen de jobs y aplicar alembic
	@$(LIB)
	banner 'MIGRATE'
	run_step 'Build jobs' dc prod build jobs
	run_step 'Up jobs' dc prod up -d jobs
	rule
	printf '\n  %sEstado antes%s\n' "$$C_BOLD" "$$C_RESET"
	_migrate_report
	printf '\n  %sAplicando migraciones pendientes%s\n\n' "$$C_BOLD" "$$C_RESET"
	dc prod exec -T jobs alembic upgrade head
	printf '\n  %sEstado despues%s\n' "$$C_BOLD" "$$C_RESET"
	_migrate_report
	printf '\n'

bootstrap: ## Crear rol, schema y grants, sembrar layers y migrar (idempotente)
	@$(LIB)
	banner 'BOOTSTRAP' 'schema mapalab'
	modo=$$(pick 'Modo' 'aplicar' 'dry-run')
	rule
	if [ "$$modo" = 'dry-run' ]; then
		./scripts/bootstrap-v14.sh --dry-run
	else
		./scripts/bootstrap-v14.sh
	fi

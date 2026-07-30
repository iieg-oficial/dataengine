-include .env
export

REPO_NAME    := dataengine
COMPOSE_PROD := -f compose.yaml

UP_PRE       := _certs
DEPLOY_PRE   := _certs
STATUS_EXTRA  = _migrate_report

include make/common.mk
include make/db.mk
include make/migrate.mk
include make/jobs.mk

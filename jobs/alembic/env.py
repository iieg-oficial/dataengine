from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config, pool

from alembic import context


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _build_url() -> str:
    direct = os.getenv("DATAENGINE_URL")
    if direct:
        return direct
    user = os.getenv("DATAENGINE_DB_USER")
    pwd = os.getenv("DATAENGINE_DB_PASSWORD")
    host = os.getenv("DATAENGINE_DB_HOST")
    port = os.getenv("DATAENGINE_DB_PORT", "5432")
    db = os.getenv("DATAENGINE_DB_NAME")
    sslmode = os.getenv("DATAENGINE_DB_SSLMODE", "require")
    if not (user and pwd and host and db):
        raise RuntimeError(
            "Conexion DataEngine no configurada. Setear DATAENGINE_URL o "
            "DATAENGINE_DB_USER/PASSWORD/HOST/NAME en el entorno."
        )
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}?sslmode={sslmode}"


target_url = _build_url()
config.set_main_option("sqlalchemy.url", target_url)

VERSION_TABLE = "alembic_version_dataengine"
VERSION_TABLE_SCHEMA = "mapalab"


def run_migrations_offline() -> None:
    context.configure(
        url=target_url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
        version_table_schema=VERSION_TABLE_SCHEMA,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=None,
            version_table=VERSION_TABLE,
            version_table_schema=VERSION_TABLE_SCHEMA,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

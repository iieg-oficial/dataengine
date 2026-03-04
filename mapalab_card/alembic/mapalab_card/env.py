from logging.config import fileConfig
from alembic import context
from core.databases.factories import DatabaseType, DatabaseFactory
from core.schemas.mapalab_card import MAPALABCardBase
from core.mapalab_card.config import MAPALABCardConfiguration

mapalab_card_conf = MAPALABCardConfiguration(env_file='core/mapalab_card/.env')

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model's MetaData for 'autogenerate' support
target_metadata = MAPALABCardBase.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL, useful for generating
    SQL scripts without connecting to the database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    """
    engine = DatabaseFactory.get_engine(
        db_type=DatabaseType.MAPALAB_CARD,
        db_url=mapalab_card_conf.db_url
    )

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_schemas=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

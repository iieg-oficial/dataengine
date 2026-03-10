# mapalab_card

Flujo ETL independiente para la ingesta de datos de **mapalab_card**.

## Estructura

```
mapalab_card_test/
├── run_bootstrap.py                     # Script de ingesta local
├── alembic/
│   └── mapalab_card/
│       ├── alembic.ini                  # Configuración Alembic
│       ├── env.py                       # Entorno de migraciones
│       ├── script.py.mako               # Template de migraciones
│       └── versions/
│           └── 377c681a4c1c_...py       # Migración inicial (47 columnas)
├── core/
│   ├── action.py                        # ABC Action
│   ├── config.py                        # ABC BaseConfiguration
│   ├── etl.py                           # Funciones extract/transform/insert/update
│   ├── source.py                        # ABC DataSource
│   ├── databases/
│   │   └── factories.py                 # DatabaseFactory + DatabaseType
│   ├── schemas/
│   │   └── mapalab_card.py              # Modelo SQLAlchemy (sincronizado con migración)
│   ├── mapalab_card/
│   │   ├── .env                         # Variables de entorno
│   │   ├── config.py                    # MAPALABCardConfiguration
│   │   ├── actions/
│   │   │   ├── actinsert.py             # MAPALABCardInsertDB (upsert)
│   │   │   └── actmapdata.py            # MapalabCardMapper (limpieza CSV)
│   │   └── sources/
│   │       └── srcdatatabular.py        # MapalabCardTabularSource
│   └── utils/
│       └── logger.py                    # Logger con Rich
├── dags/
│   └── etl_mapalab_card.py             # DAGs de Airflow (bootstrap + update)
└── data/
    └── mapalab_card/                    # Directorio para archivos CSV fuente
```

## Migraciones (Alembic)

```bash
cd mapalab_card_test

# Upgrade (crear tabla)
alembic -c alembic/mapalab_card/alembic.ini upgrade head

# Downgrade (eliminar tabla)
alembic -c alembic/mapalab_card/alembic.ini downgrade -1

# Generar nueva migración automática
alembic -c alembic/mapalab_card/alembic.ini revision --autogenerate -m "descripcion"

# Ver estado actual
alembic -c alembic/mapalab_card/alembic.ini current
```

## Ingesta local

```bash
cd mapalab_card_test

# Usando la ruta configurada en .env (MAPALAB_CARD_DATA_WORKING_DIR)
python run_bootstrap.py

```

## Configuración

Editar `core/mapalab_card/.env` con las credenciales de la base de datos:

```dotenv
MAPALAB_CARD_DB_USER=<db_user>
MAPALAB_CARD_DB_PASSWORD=<pass>
MAPALAB_CARD_DB_HOST=<host>
MAPALAB_CARD_DB_PORT=<port>
MAPALAB_CARD_DB_NAME=<db_name>
MAPALAB_CARD_DATA_WORKING_DIR=<working_dir>
```

## Airflow DAGs

- **`mapalab_card-bootstrap`**: Carga inicial (manual, `schedule=None`)
- **`mapalab_card-update`**: Actualización mensual (primer día de cada mes)

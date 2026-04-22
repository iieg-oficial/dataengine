import os
import sys

from sqlalchemy import create_engine, text

from core.utils.logger import Logger


def main() -> int:
    url = os.getenv('DATAENGINE_URL') or _build_url_from_parts()
    if not url:
        Logger.error('DATAENGINE_URL no configurado')
        return 1

    Logger.info('🔄  Refreshing public.layer_periodicity...')
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(text('SELECT public.refresh_layer_periodicity()'))
            count = conn.execute(
                text('SELECT COUNT(*) FROM public.layer_periodicity')
            ).scalar()
        Logger.info(f'✅  layer_periodicity refreshed ({count} layers)')
        return 0
    except Exception as exc:
        Logger.error(f'❌  Refresh fallo: {exc}')
        return 1
    finally:
        engine.dispose()


def _build_url_from_parts() -> str | None:
    user = os.getenv('MAPALAB_CARD_DB_USER')
    pwd = os.getenv('MAPALAB_CARD_DB_PASSWORD')
    host = os.getenv('MAPALAB_CARD_DB_HOST')
    port = os.getenv('MAPALAB_CARD_DB_PORT', '5432')
    db = os.getenv('MAPALAB_CARD_DB_NAME')
    sslmode = os.getenv('MAPALAB_CARD_DB_SSLMODE', 'require')
    if not (user and pwd and host and db):
        return None
    return f'postgresql://{user}:{pwd}@{host}:{port}/{db}?sslmode={sslmode}'


if __name__ == '__main__':
    sys.exit(main())

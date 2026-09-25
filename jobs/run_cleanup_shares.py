import os
import sys
from typing import Optional

from sqlalchemy import create_engine, text

from core.utils.logger import Logger
from core.utils.secretos import leer_secreto


SLIDING_WINDOW_DAYS = 30


def main() -> int:
    url = _build_url()
    if not url:
        Logger.error('DATAENGINE connection no configurada')
        return 1

    Logger.info('🧹  Cleanup mapalab.map_shares...')
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            sliding_deleted = conn.execute(text(f"""
                DELETE FROM mapalab.map_shares
                WHERE pinned_until IS NULL
                  AND last_accessed_at < NOW() - INTERVAL '{SLIDING_WINDOW_DAYS} days'
                RETURNING id
            """)).rowcount

            pinned_deleted = conn.execute(text("""
                DELETE FROM mapalab.map_shares
                WHERE pinned_until IS NOT NULL
                  AND pinned_until < NOW()
                RETURNING id
            """)).rowcount

        Logger.info(
            f'✅  Cleanup completed: {sliding_deleted} sliding-window + {pinned_deleted} pinned-expired'
        )
        return 0
    except Exception as exc:
        Logger.error(f'❌  Cleanup fallo: {exc}')
        return 1
    finally:
        engine.dispose()


def _build_url() -> Optional[str]:
    direct = os.getenv('DATAENGINE_URL')
    if direct:
        return direct
    user = os.getenv('DATAENGINE_DB_USER')
    pwd = leer_secreto('DATAENGINE_DB_PASSWORD')
    host = os.getenv('DATAENGINE_DB_HOST')
    port = os.getenv('DATAENGINE_DB_PORT', '5432')
    db = os.getenv('DATAENGINE_DB_NAME')
    sslmode = os.getenv('DATAENGINE_DB_SSLMODE', 'require')
    if not (user and pwd and host and db):
        return None
    return f'postgresql://{user}:{pwd}@{host}:{port}/{db}?sslmode={sslmode}'


if __name__ == '__main__':
    sys.exit(main())

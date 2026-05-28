import gzip
import os
import sys
import tempfile
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from sqlalchemy import create_engine, text

from core.utils.logger import Logger


MAX_COMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
S3_OBJECT_PREFIX = 'downloads'


def main() -> int:
    db_url = os.getenv('DATAENGINE_URL') or _build_url_from_parts()
    if not db_url:
        Logger.error('DATAENGINE_URL no configurado')
        return 1

    bucket = os.getenv('MAPALAB_AO_BUCKET')
    endpoint = os.getenv('AO_ENDPOINT')
    access_key = os.getenv('MAPALAB_AO_ACCESS_KEY')
    secret_key = os.getenv('MAPALAB_AO_SECRET_KEY')
    if not (bucket and endpoint and access_key and secret_key):
        Logger.info(
            'Acervo/mapalab no configurado (MAPALAB_AO_BUCKET, AO_ENDPOINT, '
            'MAPALAB_AO_ACCESS_KEY, MAPALAB_AO_SECRET_KEY). Skip.'
        )
        return 0

    s3 = boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='us-east-1',
        config=Config(signature_version='s3v4', retries={'max_attempts': 3}),
    )

    engine = create_engine(db_url)
    try:
        layers = _fetch_downloadable_layers(engine)
        Logger.info(f'📦  Dump CSV de capas descargables: {len(layers)} candidatas')

        ok = 0
        skipped = 0
        failed = 0
        for layer in layers:
            outcome = _dump_one(engine, s3, bucket, layer)
            if outcome == 'ok':
                ok += 1
            elif outcome == 'skip':
                skipped += 1
            else:
                failed += 1

        Logger.info(f'✅  Dump terminado: ok={ok} skip={skipped} fail={failed}')
        return 0 if failed == 0 else 2
    except Exception as exc:
        Logger.error(f'❌  Dump fallo: {exc}')
        return 1
    finally:
        engine.dispose()


def _fetch_downloadable_layers(engine) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT layer_key, layer_name_db
                FROM mapalab.layer_metadata
                WHERE downloadable = TRUE
                  AND layer_name_db IS NOT NULL
                  AND layer_name_db <> ''
                ORDER BY layer_key
                """
            )
        ).fetchall()
    out: list[dict] = []
    for layer_key, name_db in rows:
        if '.' not in name_db:
            continue
        schema, table = name_db.split('.', 1)
        out.append({'layer_key': layer_key, 'schema': schema, 'table': table})
    return out


def _dump_one(engine, s3, bucket: str, layer: dict) -> str:
    layer_key = layer['layer_key']
    schema = layer['schema']
    table = layer['table']

    if not _is_safe_identifier(schema) or not _is_safe_identifier(table):
        Logger.error(f'  ⚠️  {layer_key}: identificador inválido ({schema}.{table})')
        return 'fail'

    if not _table_exists(engine, schema, table):
        Logger.info(f'  ↪︎  {layer_key}: tabla {schema}.{table} no existe, skip')
        return 'skip'

    row_count: Optional[int] = None
    size_bytes = 0

    with tempfile.NamedTemporaryFile(prefix='dump-', suffix='.csv.gz') as tmp:
        gz = gzip.GzipFile(fileobj=tmp, mode='wb', compresslevel=6)
        raw_conn = engine.raw_connection()
        try:
            cursor = raw_conn.cursor()
            try:
                copy_sql = (
                    f'COPY (SELECT * FROM "{schema}"."{table}") '
                    f'TO STDOUT WITH CSV HEADER'
                )
                cursor.copy_expert(copy_sql, gz)
                row_count = cursor.rowcount if cursor.rowcount is not None and cursor.rowcount >= 0 else None
            finally:
                cursor.close()
        except Exception as exc:
            Logger.error(f'  ❌  {layer_key}: COPY fallo: {exc}')
            gz.close()
            raw_conn.close()
            return 'fail'
        finally:
            try:
                gz.close()
            except Exception:
                pass
            raw_conn.close()

        tmp.flush()
        size_bytes = tmp.tell()
        if size_bytes > MAX_COMPRESSED_BYTES:
            Logger.info(
                f'  ↪︎  {layer_key}: gzip pesa {size_bytes:,} bytes > límite '
                f'{MAX_COMPRESSED_BYTES:,}, skip'
            )
            return 'skip'

        tmp.seek(0)
        object_key = f'{S3_OBJECT_PREFIX}/{schema}/{table}.csv.gz'
        try:
            s3.upload_fileobj(
                tmp,
                Bucket=bucket,
                Key=object_key,
                ExtraArgs={
                    'ContentType': 'text/csv; charset=utf-8',
                    'ContentEncoding': 'gzip',
                    'ContentDisposition': f'attachment; filename="{table}.csv"',
                },
            )
        except (ClientError, BotoCoreError) as exc:
            Logger.error(f'  ❌  {layer_key}: upload fallo: {exc}')
            return 'fail'

    try:
        _upsert_metadata(engine, layer_key, schema, table, object_key, size_bytes, row_count)
    except Exception as exc:
        Logger.error(f'  ❌  {layer_key}: upsert metadata fallo: {exc}')
        return 'fail'

    rc = f'{row_count:,}' if row_count is not None else '?'
    Logger.info(f'  ✓  {layer_key} → s3://{bucket}/{object_key} ({size_bytes:,}B, {rc} filas)')
    return 'ok'


def _is_safe_identifier(value: str) -> bool:
    if not value or len(value) > 100:
        return False
    return all(c.isalnum() or c == '_' for c in value)


def _table_exists(engine, schema: str, table: str) -> bool:
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT 1 FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relkind IN ('r','v','m') "
                "AND n.nspname = :s AND c.relname = :t"
            ),
            {'s': schema, 't': table},
        ).scalar()
    return result is not None


def _upsert_metadata(
    engine,
    layer_key: str,
    schema: str,
    table: str,
    object_key: str,
    size_bytes: int,
    row_count: Optional[int],
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO mapalab.layer_downloads
                    (layer_key, db_schema, db_table, object_key, size_bytes, row_count, generated_at)
                VALUES
                    (:layer_key, :schema, :table, :object_key, :size_bytes, :row_count, now())
                ON CONFLICT (layer_key) DO UPDATE SET
                    db_schema = EXCLUDED.db_schema,
                    db_table = EXCLUDED.db_table,
                    object_key = EXCLUDED.object_key,
                    size_bytes = EXCLUDED.size_bytes,
                    row_count = EXCLUDED.row_count,
                    generated_at = EXCLUDED.generated_at
                """
            ),
            {
                'layer_key': layer_key,
                'schema': schema,
                'table': table,
                'object_key': object_key,
                'size_bytes': size_bytes,
                'row_count': row_count,
            },
        )


def _build_url_from_parts() -> Optional[str]:
    user = os.getenv('DATAENGINE_DB_USER')
    pwd = os.getenv('DATAENGINE_DB_PASSWORD')
    host = os.getenv('DATAENGINE_DB_HOST')
    port = os.getenv('DATAENGINE_DB_PORT', '5432')
    db = os.getenv('DATAENGINE_DB_NAME')
    sslmode = os.getenv('DATAENGINE_DB_SSLMODE', 'require')
    if not (user and pwd and host and db):
        return None
    return f'postgresql://{user}:{pwd}@{host}:{port}/{db}?sslmode={sslmode}'


if __name__ == '__main__':
    sys.exit(main())

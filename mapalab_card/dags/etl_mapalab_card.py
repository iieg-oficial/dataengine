import sys
sys.path.append('/opt/airflow')

from airflow.sdk import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
from core.etl import insert
from core.mapalab_card.config import MAPALABCardConfiguration
from core.mapalab_card.actions.actinsert import MAPALABCardInsertDB
from core.mapalab_card.sources.srcdatatabular import MapalabCardTabularSource


config = MAPALABCardConfiguration()


def etl_insert() -> None:
    """Carga inicial o actualización de mapalab_card desde CSV."""
    insert(
        src=MapalabCardTabularSource(),
        action=MAPALABCardInsertDB()
    )


# ── Bootstrap DAG (carga inicial, ejecución manual) ──────────────────────────

default_args = {
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='mapalab_card-bootstrap',
    default_args=default_args,
    description='Carga inicial de la tabla mapalab_card desde CSV.',
    schedule=None,
    catchup=False,
    tags=['mapalab_card', 'etl', 'bootstrap']
):
    insert_task = PythonOperator(
        task_id='mapalab_card-data-insert',
        python_callable=etl_insert,
    )


# ── Update DAG (actualización periódica mensual) ─────────────────────────────

with DAG(
    dag_id='mapalab_card-update',
    default_args=default_args,
    description='Actualización mensual de mapalab_card (upsert desde CSV).',
    schedule='0 0 1 * *',  # Primer día de cada mes
    catchup=False,
    tags=['mapalab_card', 'etl', 'update']
):
    update_task = PythonOperator(
        task_id='mapalab_card-data-update',
        python_callable=etl_insert,
    )

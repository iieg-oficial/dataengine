"""Script de bootstrap para ejecutar el flujo ETL de mapalab_card localmente.

Uso:
    cd mapalab_card_test
    python run_bootstrap.py                              # usa CSV de data_work_dir (.env)
    python run_bootstrap.py /ruta/a/mi/archivo.csv       # CSV específico
"""
import sys
import os

# Agregar el directorio actual al path para resolver imports de core.*
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.etl import insert
from core.mapalab_card.config import MAPALABCardConfiguration
from core.mapalab_card.actions.actinsert import MAPALABCardInsertDB
from core.mapalab_card.sources.srcdatatabular import MapalabCardTabularSource
from core.utils.logger import Logger


def main() -> None:
    config = MAPALABCardConfiguration()

    # Permitir pasar ruta de CSV como argumento
    csv_path = sys.argv[1] if len(sys.argv) > 1 else config.data_work_dir

    Logger.info(f"🚀 Iniciando ingesta de mapalab_card desde: {csv_path}")

    insert(
        src=MapalabCardTabularSource(input=csv_path),
        action=MAPALABCardInsertDB()
    )

    Logger.info("✅ Ingesta completada.")


if __name__ == '__main__':
    main()

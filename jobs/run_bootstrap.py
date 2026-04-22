import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.etl import insert
from core.mapalab_card.config import MAPALABCardConfiguration
from core.mapalab_card.actions.actinsert import MAPALABCardInsertDB
from core.mapalab_card.sources.srcdatatabular import MapalabCardTabularSource
from core.utils.logger import Logger


_DEPRECATION_NOTICE = """
⚠️  DEPRECATED: La ingesta desde Google Sheet a public.mapalab_card ya no es la
    fuente de verdad. La nueva fuente es mapalab.layer_metadata + mapalab.layer_stats
    (editables desde mariachi /administrador/mapalab/layers).

    Este script se mantiene como fallback solo para casos excepcionales.
    Para correrlo de todos modos, usa:
        FORCE_LEGACY_ETL=1 python run_bootstrap.py
"""


def main() -> None:
    if os.getenv('FORCE_LEGACY_ETL') != '1':
        Logger.warning(_DEPRECATION_NOTICE)
        sys.exit(0)

    config = MAPALABCardConfiguration()

    csv_path = sys.argv[1] if len(sys.argv) > 1 else config.data_work_dir

    Logger.info(f"🚀 Iniciando ingesta de mapalab_card desde: {csv_path}")

    insert(
        src=MapalabCardTabularSource(input=csv_path),
        action=MAPALABCardInsertDB()
    )

    Logger.info("✅ Ingesta completada.")


if __name__ == '__main__':
    main()

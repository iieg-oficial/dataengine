import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.etl import insert
from core.mapalab_card.config import MAPALABCardConfiguration
from core.mapalab_card.actions.actinsert import MAPALABCardInsertDB
from core.mapalab_card.sources.srcdatatabular import MapalabCardTabularSource
from core.utils.logger import Logger


def main() -> None:
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

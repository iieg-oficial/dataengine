import os
import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from core.action import Action
from core.utils.logger import Logger
from core.mapalab_card.config import MAPALABCardConfiguration
from core.databases.factories import DatabaseFactory, DatabaseType
from sqlalchemy import MetaData, Table, select


@dataclass
class MAPALABCardBackupDB(Action):
    def execute(self, input: pd.DataFrame = None) -> None:
        mapalab_card_conf = MAPALABCardConfiguration()
        engine = DatabaseFactory.get_engine(
            db_type=DatabaseType.MAPALAB_CARD,
            db_url=mapalab_card_conf.db_url
        )

        metadata = MetaData()
        tabla = Table(
            "mapalab_card",
            metadata,
            autoload_with=engine
        )

        try:
            with engine.connect() as conn:
                result = conn.execute(select(tabla))
                rows = result.fetchall()
                columns = result.keys()

            Logger.info(f"Len rows: {len(rows)}")
            Logger.info(f"Rows preview: {rows[:5]}")
            if not rows:
                return
            
            df_backup = pd.DataFrame(rows, columns=columns)

            # Directorio de backups relativo al proyecto
            backup_dir = os.path.join(
                os.path.dirname(__file__), '..', '..', '..', 'data', 'backups'
            )
            backup_dir = os.path.normpath(backup_dir)
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"mapalab_card_backup_{timestamp}.csv")

            df_backup.to_csv(backup_file, index=False, encoding="utf-8")
            Logger.info(f"💾 Backup generado: {backup_file} ({len(df_backup)} registros)")

        except Exception as e:
            Logger.error(f"❌ Error durante el backup: {e}")
            raise

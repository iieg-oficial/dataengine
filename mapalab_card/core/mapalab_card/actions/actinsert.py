import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from core.action import Action
from core.utils.logger import Logger
from core.mapalab_card.config import MAPALABCardConfiguration
from core.databases.factories import DatabaseFactory, DatabaseType
from core.schemas.mapalab_card import MapalabCard
from sqlalchemy import MetaData, Table, delete, text


@dataclass
class MAPALABCardInsertDB(Action):
    """Acción de INSERT: borra los datos existentes y vuelve a insertar todo desde el CSV fuente."""

    def execute(self, input: pd.DataFrame) -> None:
        card_df = input

        mapalab_card_conf = MAPALABCardConfiguration()
        engine = DatabaseFactory.get_engine(
            db_type=DatabaseType.MAPALAB_CARD,
            db_url=mapalab_card_conf.db_url
        )

        registros = card_df.to_dict(orient="records")

        # Agregar created_at con la fecha de ingesta (solo fecha, sin hora)
        fecha_ingesta = datetime.today().date()
        for registro in registros:
            registro['created_at'] = fecha_ingesta

        metadata = MetaData()
        tabla = Table(
            "mapalab_card",
            metadata,
            autoload_with=engine
        )

        try:
            with engine.begin() as conn:
                # Borrar todos los registros existentes antes de insertar
                conn.execute(delete(tabla))
                Logger.info("🗑️  Datos existentes eliminados de mapalab_card.")

                # Reiniciar la secuencia del id a 1
                conn.execute(text("ALTER SEQUENCE mapalab_card_id_seq RESTART WITH 1"))
                Logger.info("🔄  Secuencia de id reiniciada.")

                # Insertar todos los registros del CSV fuente
                conn.execute(tabla.insert(), registros)

            Logger.info("✅ Inserción ejecutada correctamente.")

        except Exception as e:
            Logger.error(f"❌ Error durante la inserción: {e}")
            raise

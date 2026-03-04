import os
from dataclasses import dataclass, field
from core.source import DataSource
from core.utils.logger import Logger
import pandas as pd
from core.mapalab_card.actions.actmapdata import MapalabCardMapper


@dataclass
class MapalabCardTabularSource(DataSource):
    """Lee el CSV desde sources/mapalab_card.csv y lo limpia/mapea."""
    input: str = field(default=os.path.join(os.path.dirname(__file__), 'mapalab_card.csv'))
    mapper: MapalabCardMapper = field(default_factory=MapalabCardMapper)

    def get(self) -> pd.DataFrame:
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'mapalab_card', 'mapalab_card.csv')
        csv_path = os.path.normpath(csv_path)
        Logger.info(f"📄 Leyendo CSV desde: {csv_path}")
        file_csv = pd.read_csv(csv_path)
        file_mapped = self.mapper.clean_csv(file_csv)
        Logger.info(f"📊 {len(file_mapped)} registros leídos y mapeados.")
        return file_mapped

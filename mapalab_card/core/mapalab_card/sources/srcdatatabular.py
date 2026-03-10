import os
from dataclasses import dataclass, field
from xmlrpc import client
from core.source import DataSource
from core.utils.logger import Logger
import pandas as pd
from core.mapalab_card.actions.actmapdata import MapalabCardMapper
from core.mapalab_card.config import MAPALABCardConfiguration
import gspread
from google.oauth2.service_account import Credentials

@dataclass
class MapalabCardTabularSource(DataSource):
    input: str = field(default=os.path.join(os.path.dirname(__file__), 'mapalab_card.csv'))
    mapper: MapalabCardMapper = field(default_factory=MapalabCardMapper)


    def get(self) -> pd.DataFrame:
        config = MAPALABCardConfiguration()

        SCOPES = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]

        creds_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', config.google_credentials_path)
        creds_path = os.path.normpath(creds_path)
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        client = gspread.authorize(creds)

        Logger.info(f"📄 Leyendo desde Google Sheets: {config.google_sheet_url}")
        file_sheet = client.open_by_url(config.google_sheet_url)
        file_sheet.fetch_sheet_metadata()
        Logger.info("🔄 Cache actualizado desde Google Sheets.")
        file_csv = pd.DataFrame(file_sheet.sheet1.get_all_records())
        
        file_mapped = self.mapper.clean_csv(file_csv)
        Logger.info(f"📊 {len(file_mapped)} registros leídos y mapeados.")
        return file_mapped

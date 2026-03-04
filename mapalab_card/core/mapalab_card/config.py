import os

from dataclasses import dataclass, field
from typing import Any
from core.config import BaseConfiguration


@dataclass
class MAPALABCardConfiguration(BaseConfiguration):
    env_file: str = field(default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
    config: dict[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        super().__init__(self.env_file)

    def _load_config(self) -> None:
        self.config = {
            'MAPALAB_CARD_DB_USER': os.getenv('MAPALAB_CARD_DB_USER'),
            'MAPALAB_CARD_DB_PASSWORD': os.getenv('MAPALAB_CARD_DB_PASSWORD'),
            'MAPALAB_CARD_DB_HOST': os.getenv('MAPALAB_CARD_DB_HOST'),
            'MAPALAB_CARD_DB_PORT': os.getenv('MAPALAB_CARD_DB_PORT'),
            'MAPALAB_CARD_DB_NAME': os.getenv('MAPALAB_CARD_DB_NAME'),
            'MAPALAB_CARD_DATA_WORKING_DIR': os.getenv('MAPALAB_CARD_DATA_WORKING_DIR'),
            'MAPALAB_CARD_DATA_ERROR_DIR': os.getenv('MAPALAB_CARD_DATA_ERROR_DIR'),
            'MAPALAB_CARD_INSERT_DATE': os.getenv('MAPALAB_CARD_INSERT_DATE'),
            'MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH': os.getenv('MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH'),
            'MAPALAB_CARD_GOOGLE_SHEET_URL': os.getenv('MAPALAB_CARD_GOOGLE_SHEET_URL'),
        }

    @property
    def data_work_dir(self) -> str:
        return self.get_property('MAPALAB_CARD_DATA_WORKING_DIR')

    @property
    def data_error_dir(self) -> str:
        return self.get_property('MAPALAB_CARD_DATA_ERROR_DIR')

    @property
    def db_user(self) -> str | None:
        return self.get_property('MAPALAB_CARD_DB_USER')

    @property
    def db_password(self) -> str | None:
        return self.get_property('MAPALAB_CARD_DB_PASSWORD')

    @property
    def db_host(self) -> str | None:
        return self.get_property('MAPALAB_CARD_DB_HOST')

    @property
    def db_port(self) -> str | None:
        return self.get_property('MAPALAB_CARD_DB_PORT')

    @property
    def db_name(self) -> str | None:
        return self.get_property('MAPALAB_CARD_DB_NAME')

    @property
    def insert_date(self) -> str | None:
        return self.get_property('MAPALAB_CARD_INSERT_DATE')

    @property
    def google_credentials_path(self) -> str | None:
        return self.get_property('MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH')

    @property
    def google_sheet_url(self) -> str | None:
        return self.get_property('MAPALAB_CARD_GOOGLE_SHEET_URL')

    @property
    def db_url(self) -> str:
        return f'postgresql+psycopg2://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}'

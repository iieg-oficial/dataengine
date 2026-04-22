from enum import Enum, auto
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.utils.logger import Logger
from typing import Any


class DatabaseType(Enum):
    MAPALAB_CARD = auto()


class DatabaseFactory:
    instances = dict()

    @classmethod
    def get_engine(
        cls,
        db_type: DatabaseType,
        db_url: str,
        echo: bool = False
    ):
        if db_type not in cls.instances:
            engine = create_engine(db_url, echo=echo)
            cls.instances[db_type] = {
                'engine': engine,
                'session_factory': sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=engine
                )
            }
            Logger.info(f'🔓  Engine for {db_type.name} database initialized.')
        return cls.instances[db_type]['engine']

    @classmethod
    def get_session_factory(cls, db_type: DatabaseType) -> Any:
        if db_type not in cls.instances:
            raise ValueError(f"🔴  Engine for {db_type.name} not initialized.")
        return cls.instances[db_type]['session_factory']

    @classmethod
    def close_all(cls) -> None:
        for db_type, instance in cls.instances.items():
            instance['engine'].dispose()
            Logger.info(f'🔒  Engine for {db_type.name} database disposed.')
        cls.instances.clear()

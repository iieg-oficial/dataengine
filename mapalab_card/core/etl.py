from core.source import DataSource
from core.action import Action
from core.utils.logger import Logger


def extract(src: DataSource, action: Action = None) -> None:
    Logger.info('📚  Data Extraction.')
    Logger.info('🔍  Looking for Sources.')
    sources = src.get()
    Logger.info('✨  Extracting Data.')
    action.execute(input=sources)


def transform(src: DataSource, action: Action = None) -> None:
    Logger.info('📚  Data Processing.')
    Logger.info('🔍  Looking for Sources.')
    sources = src.get()
    Logger.info('✨  Processing Data.')
    action.execute(input=sources)


def update(src: DataSource, action: Action = None) -> None:
    Logger.info('📚  Data Updating.')
    Logger.info('🔍  Looking for Sources.')
    sources = src.get()
    Logger.info('✨  Updating Data.')
    action.execute(input=sources)


def insert(src: DataSource, action: Action = None) -> None:
    Logger.info('📚  Data Insertion.')
    Logger.info('🔍  Looking for Sources.')
    sources = src.get()
    Logger.info('✨  Adding Data.')
    action.execute(input=sources)

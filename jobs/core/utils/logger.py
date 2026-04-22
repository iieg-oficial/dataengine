import logging
import os

from rich.logging import RichHandler
from typing import Any


FORMAT = "%(message)s"
FILE_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

_LOG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'logs')
_LOG_DIR = os.path.normpath(_LOG_DIR)
os.makedirs(_LOG_DIR, exist_ok=True)

_file_handler = logging.FileHandler(
    os.path.join(_LOG_DIR, "jobs.log"), encoding="utf-8"
)
_file_handler.setLevel(logging.INFO)
_file_handler.setFormatter(logging.Formatter(FILE_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))

logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger("rich")
log.addHandler(_file_handler)


class Logger:

    @staticmethod
    def info(message: Any) -> None:
        log.info(f'{message}')

    @staticmethod
    def warning(message: Any) -> None:
        log.warning(f'{message}')

    @staticmethod
    def error(message: Any) -> None:
        log.error(f'{message}')

    @staticmethod
    def critical(message: Any) -> None:
        log.critical(f'{message}')

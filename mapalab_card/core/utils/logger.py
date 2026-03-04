import logging

from rich.logging import RichHandler
from typing import Any


FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger("rich")


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

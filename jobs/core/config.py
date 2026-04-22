import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from dotenv import load_dotenv
from typing import Any


class BaseConfiguration(ABC):
    def __init__(self, env_file: str | None = None) -> None:
        if env_file:
            load_dotenv(env_file, override=True)
        self.config: dict[str, Any] = dict()
        self._load_config()

    @abstractmethod
    def _load_config(self) -> None: ...

    def get_property(self, property_name: str, default: Any = None) -> Any:
        return self.config.get(property_name, default)

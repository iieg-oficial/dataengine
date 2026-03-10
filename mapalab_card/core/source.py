from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Any


@dataclass
class DataSource(ABC):
    input: str

    @abstractmethod
    def get(self) -> Any: ...

from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Any


@dataclass
class Action(ABC):
    @abstractmethod
    def execute(self, input: Any, *args: Any, **kwargs: Any) -> Any: ...

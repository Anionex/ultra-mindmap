from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Document:
    title: str
    content: str


class BaseEngine(ABC):
    name: str
    display_name: str
    description: str

    @abstractmethod
    def get_params_schema(self) -> dict:
        pass

    @abstractmethod
    def generate(self, documents: list[Document], params: dict) -> dict:
        pass


_registry: dict[str, BaseEngine] = {}


def register_engine(engine: BaseEngine):
    _registry[engine.name] = engine


def get_engine(name: str) -> BaseEngine:
    from ..utils.errors import AppError
    if name not in _registry:
        raise AppError(code="INVALID_ENGINE", message=f"未知的生成引擎: {name}")
    return _registry[name]


def list_engines() -> list[BaseEngine]:
    return list(_registry.values())

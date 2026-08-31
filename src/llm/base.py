from abc import ABC, abstractmethod

from models.context import Context


class BaseLLM(ABC):

    @abstractmethod
    def generate(self, context: Context) -> str:
        pass
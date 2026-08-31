from collections.abc import Iterable
from dataclasses import dataclass, field

from models.context_element import ContextElement


@dataclass
class Context:

    _elements: list[ContextElement] = field(default_factory=list)

    def add(
        self,
        role: str,
        content: str,
    ) -> None:

        self._elements.append(

            ContextElement(
                role=role,
                content=content,
            )

        )

    def extend(
        self,
        elements: Iterable[ContextElement],
    ) -> None:

        self._elements.extend(elements)

    def get(self) -> list[ContextElement]:

        return list(self._elements)
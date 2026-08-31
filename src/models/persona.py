from dataclasses import dataclass


@dataclass
class Persona:
    """
    Represents the assistant's persona.
    """

    name: str
    description: str

    version: int = 1
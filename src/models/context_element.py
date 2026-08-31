from dataclasses import dataclass


@dataclass
class ContextElement:
    """
    Represents one piece of context before it is converted
    into LLM messages.
    """

    role: str
    content: str
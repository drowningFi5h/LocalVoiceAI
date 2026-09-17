from dataclasses import dataclass


@dataclass
class Interaction:
    """
    Represents a single conversational exchange.
    """

    user_message: str

    assistant_reply: str
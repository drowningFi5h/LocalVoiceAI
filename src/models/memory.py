from dataclasses import dataclass
from datetime import datetime


@dataclass
class Memory:
    """
    Represents a single long-term memory.
    """

    memory_type: str
    category: str
    key: str
    value: str

    importance: float = 0.5
    confidence: float = 1.0

    id: int | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_used: datetime | None = None

    use_count: int = 0
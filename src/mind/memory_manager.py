from models.memory import Memory
from models.memory_candidate import MemoryCandidate

from storage.repositories.memory_repository import MemoryRepository


class MemoryManager:

    def __init__(
        self,
        repository: MemoryRepository,
    ):

        self.repository = repository

    def store(
        self,
        candidate: MemoryCandidate,
    ) -> None:

        if candidate.confidence < 0.65:
            return

        if candidate.importance < 0.50:
            return

        memory = Memory(

            memory_type=candidate.memory_type,

            category=candidate.category,

            key=candidate.key,

            value=candidate.value,

            importance=candidate.importance,

            confidence=candidate.confidence,

        )

        self._store_memory(memory)

    def _store_memory(
        self,
        memory: Memory,
    ) -> None:

        existing_memory = self.repository.find_by_identity(

            memory.memory_type,

            memory.category,

            memory.key,

        )

        if existing_memory is None:

            self.repository.add(memory)

            return

        existing_memory.value = memory.value

        existing_memory.importance = max(

            existing_memory.importance,

            memory.importance,

        )

        existing_memory.confidence = min(

            1.0,

            existing_memory.confidence + 0.05,

        )

        existing_memory.use_count += 1

        self.repository.update(existing_memory)

    def get_user_memories(self) -> list[Memory]:

        return self.repository.get_all("user")

    def get_persona_memories(self) -> list[Memory]:

        return self.repository.get_all("persona")
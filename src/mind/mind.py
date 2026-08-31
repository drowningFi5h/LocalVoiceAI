from models.interaction import Interaction

from mind.context_builder import ContextBuilder
from mind.memory_extractor import MemoryExtractor
from mind.memory_manager import MemoryManager

from core.persona_loader import PersonaLoader


class Mind:

    def __init__(
        self,
        llm,
        working_memory,
        memory_manager: MemoryManager,
    ):

        self.llm = llm

        self.working_memory = working_memory

        self.memory_manager = memory_manager

        self.context_builder = ContextBuilder()

        self.memory_extractor = MemoryExtractor(llm)

        self.persona = PersonaLoader.load()

    def respond(
        self,
        user_message: str,
    ) -> str:

        self.working_memory.add_user(
            user_message
        )

        context = self.context_builder.build(

            self.persona.description,

            self.memory_manager.get_user_memories(),

            self.working_memory.get_messages(),

        )

        assistant_reply = self.llm.generate(
            context
        )

        self.working_memory.add_assistant(
            assistant_reply
        )

        interaction = Interaction(

            user_message=user_message,

            assistant_reply=assistant_reply,

        )

        candidates = self.memory_extractor.extract(
            interaction
        )

        for candidate in candidates:

            self.memory_manager.store(
                candidate
            )

        return assistant_reply
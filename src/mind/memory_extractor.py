from mind.candidate_parser import CandidateParser

from core.instruction_loader import InstructionLoader
from models.context import Context
from models.interaction import Interaction
from models.memory_candidate import MemoryCandidate


class MemoryExtractor:

    def __init__(self, llm):

        self.llm = llm

        self.instructions = InstructionLoader.load(
            "memory_extractor"
        )

    def extract(
        self,
        interaction: Interaction,
    ) -> list[MemoryCandidate]:

        context = Context()

        context.add(
            "system",
            self.instructions,
        )

        context.add(
            "user",
            f"""
User Message:
{interaction.user_message}

Assistant Reply:
{interaction.assistant_reply}
"""
        )

        llm_response = self.llm.generate(context)

        return CandidateParser.parse(llm_response)
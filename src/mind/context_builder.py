from models.context import Context
from models.memory import Memory


class ContextBuilder:

    def build(
        self,
        persona: str,
        memories: list[Memory],
        conversation: list[dict[str, str]],
    ) -> Context:

        context = Context()

        # Persona
        context.add(
            "system",
            persona,
        )

        # Long-term memory
        if memories:

            memory_text = "\n".join(

                f"- {memory.category}.{memory.key}: {memory.value}"

                for memory in memories

            )

            context.add(

                "system",

                f"Known information about the user:\n{memory_text}",

            )

        # Current conversation
        for message in conversation:

            context.add(

                message["role"],

                message["content"],

            )

        return context
from models.memory import Memory


class DuplicateResolver:

    """
    Determines whether a memory already exists.
    """

    @staticmethod
    def same_memory(existing: Memory, incoming: Memory):

        return (

            existing.memory_type == incoming.memory_type

            and existing.category == incoming.category

            and existing.key == incoming.key

        )
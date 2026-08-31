from typing import List


class WorkingMemory:
    """
    Stores the current conversation.
    Cleared when the session ends.
    """

    def __init__(self):

        self._messages: List[dict[str, str]] = []

    def add_user(self, message: str):

        self._messages.append(

            {
                "role": "user",
                "content": message,
            }

        )

    def add_assistant(self, message: str):

        self._messages.append(

            {
                "role": "assistant",
                "content": message,
            }

        )

    def get_messages(self) -> List[dict[str, str]]:

        return list(self._messages)

    def clear(self):

        self._messages.clear()
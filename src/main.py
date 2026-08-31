from llm.llama_cpp import LlamaCppBackend

from mind.mind import Mind
from mind.memory_manager import MemoryManager
from mind.working_memory import WorkingMemory

from storage.database import Database
from storage.repositories.memory_repository import MemoryRepository


def main():

    database = Database()

    repository = MemoryRepository(database)

    memory_manager = MemoryManager(repository)

    llm = LlamaCppBackend()

    working_memory = WorkingMemory()

    mind = Mind(

        llm=llm,

        working_memory=working_memory,

        memory_manager=memory_manager,

    )

    print("LocalVoiceAI started. Type 'exit' to quit.\n")

    while True:

        user_message = input("You > ").strip()

        if user_message.lower() in {"exit", "quit"}:
            break

        assistant_reply = mind.respond(
            user_message
        )

        print(f"\nAI > {assistant_reply}\n")

    database.close()


if __name__ == "__main__":

    main()
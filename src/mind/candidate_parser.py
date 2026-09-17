import json

from models.memory_candidate import MemoryCandidate


class CandidateParser:
    """
    Converts raw LLM JSON into MemoryCandidate objects.
    """

    @staticmethod
    def parse(response: str) -> list[MemoryCandidate]:

        try:
            raw_candidates = json.loads(response)

        except json.JSONDecodeError:

            print("Invalid JSON returned by MemoryExtractor.")

            print(response)

            return []

        candidates = []

        for candidate in raw_candidates:

            try:

                candidates.append(

                    MemoryCandidate(

                        memory_type=candidate["memory_type"],

                        category=candidate["category"],

                        key=candidate["key"],

                        value=candidate["value"],

                        importance=float(candidate["importance"]),

                        confidence=float(candidate["confidence"])

                    )

                )

            except (KeyError, ValueError, TypeError):

                continue

        return candidates
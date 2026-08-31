from pathlib import Path


class InstructionLoader:

    BASE = Path("src/instructions")

    @classmethod
    def load(cls, name: str) -> str:

        path = cls.BASE / f"{name}.md"

        return path.read_text(encoding="utf-8")
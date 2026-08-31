from pathlib import Path

from models.persona import Persona


class PersonaLoader:
    """
    Loads assistant personas from the configuration directory.
    """

    BASE_PATH = Path("configs/personas")

    @classmethod
    def load(
        cls,
        name: str = "default",
    ) -> Persona:

        persona_path = cls.BASE_PATH / f"{name}.md"

        if not persona_path.exists():

            raise FileNotFoundError(

                f"Persona '{name}' not found: {persona_path}"

            )

        return Persona(

            name=name,

            description=persona_path.read_text(
                encoding="utf-8",
            ).strip(),

        )
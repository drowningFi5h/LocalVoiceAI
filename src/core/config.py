from pathlib import Path

import yaml


class Config:

    def __init__(
        self,
        path: str = "configs/config.yaml",
    ):

        config_path = Path(path)

        if not config_path.exists():

            raise FileNotFoundError(

                f"Config file not found: {config_path}"

            )

        with config_path.open(
            "r",
            encoding="utf-8",
        ) as f:

            self.data = yaml.safe_load(f)

    @property
    def server(self):

        return self.data["server"]

    @property
    def model(self):

        return self.data["model"]

    @property
    def conversation(self):

        return self.data["conversation"]

    @property
    def persona(self):

        return self.data["persona"]

    @property
    def database(self):

        return self.data["database"]
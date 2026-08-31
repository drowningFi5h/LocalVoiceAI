from litellm import completion

from core.config import Config
from llm.base import BaseLLM
from models.context import Context


class LlamaCppBackend(BaseLLM):

    def __init__(self):

        cfg = Config()

        self.base_url = cfg.server["base_url"]

        self.api_key = cfg.server["api_key"]

        self.provider = cfg.server["provider"]
        
        self.model = f"{self.provider}/{cfg.model['name']}"

        self.temperature = 0.7

    def _build_request(
        self,
        context: Context,
    ) -> list[dict[str, str]]:

        return [
            {
                "role": element.role,
                "content": element.content,
            }
            for element in context.get()
        ]

    def generate(
        self,
        context: Context,
    ) -> str:

        response = completion(

            model=self.model,

            api_base=self.base_url,

            api_key=self.api_key,

            messages=self._build_request(context),

            temperature=self.temperature,

        )

        return response.choices[0].message.content
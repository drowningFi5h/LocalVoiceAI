from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI


class Models:
    def __init__(self, settings):
        self.settings = settings

    def chat(self, provider):
        if provider == "local":
            if self.settings.local_backend == "lmstudio":
                return ChatOpenAI(
                    base_url=self.settings.lmstudio_url,
                    model=self.settings.lmstudio_model,
                    api_key=self.settings.lmstudio_api_key or "lm-studio",
                    temperature=0,
                    timeout=120,
                    max_retries=0,
                    max_tokens=512,
                    stream_usage=True,
                )
            return ChatOllama(
                base_url=self.settings.ollama_url,
                model=self.settings.ollama_model,
                temperature=0,
                reasoning=False,
                num_ctx=8192,
                num_predict=512,
                client_kwargs={"timeout": 90},
            )
        if provider != "cloud" or self.settings.offline or not self.settings.cloud_api_key:
            raise ValueError(
                "Cloud mode is unavailable. Configure LVA_CLOUD_API_KEY and disable offline mode."
            )
        if self.settings.cloud_backend == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=self.settings.cloud_model,
                google_api_key=self.settings.cloud_api_key,
                vertexai=False,
                temperature=0,
                max_output_tokens=2048,
                include_thoughts=False,
                timeout=60,
                max_retries=1,
            )
        return ChatOpenAI(
            model=self.settings.cloud_model,
            api_key=self.settings.cloud_api_key,
            base_url=self.settings.cloud_base_url,
            temperature=0,
            timeout=60,
            max_retries=1,
            max_tokens=512,
        )

    async def complete(self, provider, system, text):
        result = await self.chat(provider).ainvoke([SystemMessage(system), HumanMessage(text)])
        return visible_text(result.content)

    async def stream(self, provider, system, text):
        async for chunk in self.chat(provider).astream([SystemMessage(system), HumanMessage(text)]):
            text = visible_text(chunk.content)
            if text:
                yield {"text": text}
            if chunk.usage_metadata:
                yield {"usage": chunk.usage_metadata}


def visible_text(content):
    """Render only answer text, excluding thought/signature/tool metadata."""
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "") for block in content if isinstance(block, dict) and block.get("type") == "text"
    )

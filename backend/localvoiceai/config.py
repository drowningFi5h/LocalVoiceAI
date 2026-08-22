from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LVA_", env_file=".env", extra="ignore")
    data_dir: Path = Path("data")
    local_backend: Literal["ollama", "lmstudio"] = "ollama"
    lmstudio_url: str = "http://localhost:1234/v1"
    lmstudio_model: str = "qwen/qwen3-vl-4b"
    lmstudio_api_key: str = ""
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"
    cloud_model: str = "gpt-4.1-mini"
    cloud_backend: Literal["openai", "gemini"] = "openai"
    cloud_api_key: str = ""
    cloud_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    whisper_model: str = "base.en"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    kokoro_voice: str = "af_heart"
    offline: bool = False
    max_upload_bytes: int = 20 * 1024 * 1024
    max_page_bytes: int = 5 * 1024 * 1024
    origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8017",
        "http://127.0.0.1:8017",
    ]

    @field_validator("lmstudio_url")
    @classmethod
    def validate_local_endpoint(cls, value):
        parsed = urlparse(value)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("LM Studio must use a loopback HTTP(S) endpoint without URL credentials.")
        return value.rstrip("/")

    @property
    def local_model(self):
        return self.lmstudio_model if self.local_backend == "lmstudio" else self.ollama_model

    def prepare(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "uploads").mkdir(exist_ok=True)
        (self.data_dir / "models").mkdir(exist_ok=True)

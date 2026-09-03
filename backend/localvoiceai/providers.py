"""Explicit, memory-only cloud credentials for this single-user server."""

from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator

PROVIDERS = {
    "gemini": ("Google Gemini", "gemini", "https://generativelanguage.googleapis.com"),
    "openai": ("OpenAI", "openai", "https://api.openai.com/v1"),
    "groq": ("Groq", "openai", "https://api.groq.com/openai/v1"),
    "openrouter": ("OpenRouter", "openai", "https://openrouter.ai/api/v1"),
}


class ProviderInput(BaseModel):
    id: str | None = None
    name: str = Field(default="", max_length=80)
    provider: Literal["gemini", "openai", "groq", "openrouter"]
    model: str = Field(min_length=1, max_length=180)
    api_key: SecretStr | None = None

    @field_validator("model")
    @classmethod
    def clean_model(cls, value):
        if not value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError("Enter a valid model identifier.")
        return value.strip()

    @field_validator("api_key")
    @classmethod
    def clean_key(cls, value):
        key = value.get_secret_value().strip()
        if not 8 <= len(key) <= 4096 or any(c.isspace() for c in key):
            raise ValueError("Enter a valid API key without whitespace.")
        return SecretStr(key)


def provider_name(settings):
    if settings.cloud_backend == "gemini":
        return "Google Gemini"
    for name, _, endpoint in PROVIDERS.values():
        if settings.cloud_base_url.rstrip("/") == endpoint:
            return name
    return "Configured provider"

import pytest
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from localvoiceai.config import Settings
from localvoiceai.models import Models, visible_text
from pydantic import ValidationError


def test_lmstudio_is_local_even_in_offline_mode():
    settings = Settings(
        _env_file=None, local_backend="lmstudio", offline=True, lmstudio_url="http://localhost:1234/v1/"
    )
    model = Models(settings).chat("local")
    assert isinstance(model, ChatOpenAI)
    assert model.openai_api_base == "http://localhost:1234/v1"
    assert model.model_name == settings.local_model == "qwen/qwen3-vl-4b"
    with pytest.raises(ValueError):
        Models(settings).chat("cloud")


def test_ollama_remains_default():
    settings = Settings(_env_file=None)
    assert isinstance(Models(settings).chat("local"), ChatOllama)
    assert settings.local_model == settings.ollama_model


@pytest.mark.parametrize("url", ["https://example.com/v1", "http://user:secret@localhost:1234/v1"])
def test_local_label_cannot_point_to_external_provider(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, lmstudio_url=url)


def test_gemini_is_explicit_and_never_replaces_local():
    from langchain_google_genai import ChatGoogleGenerativeAI

    config = Settings(
        _env_file=None, cloud_backend="gemini", cloud_model="gemini-flash-latest", cloud_api_key="test-key"
    )
    models = Models(config)
    assert isinstance(models.chat("local"), ChatOllama)
    remote = models.chat("cloud")
    assert isinstance(remote, ChatGoogleGenerativeAI)
    assert remote.include_thoughts is False
    config.offline = True
    with pytest.raises(ValueError):
        models.chat("cloud")


def test_gemini_content_blocks_exclude_reasoning():
    assert (
        visible_text(
            [{"type": "thinking", "text": "private reasoning"}, {"type": "text", "text": "Cited answer [1]."}]
        )
        == "Cited answer [1]."
    )

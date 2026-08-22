import hashlib
from types import SimpleNamespace

import pytest
from langchain_core.embeddings import Embeddings
from localvoiceai.config import Settings
from localvoiceai.db import Database


@pytest.fixture
def settings(tmp_path):
    config = Settings(data_dir=tmp_path, _env_file=None)
    config.prepare()
    return config


@pytest.fixture
def db(settings):
    database = Database(settings.data_dir / "test.sqlite")
    yield database
    database.close()


class TestEmbeddings(Embeddings):
    __test__ = False

    def embed_documents(self, texts):
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text):
        # Deterministic test double, deliberately not advertised as semantic retrieval.
        out = [0.0] * 16
        for token in text.lower().split():
            out[hashlib.md5(token.encode()).digest()[0] % 16] += 1
        return out


class FakeModels:
    settings = SimpleNamespace(local_model="test-model", cloud_model="test-cloud", embedding_model="test")

    def __init__(self, sufficient=True):
        self.sufficient = sufficient
        self.calls = []

    async def complete(self, provider, system, text):
        self.calls.append((system, text))
        if "Assess whether" in system:
            return '{"sufficient": ' + str(self.sufficient).lower() + ', "reason": "Evidence checked."}'
        return "station battery capacity"

    async def stream(self, provider, system, text):
        yield {"text": "The battery holds 40 kWh. "}
        yield {"text": "[1]"}
        yield {"usage": {"input_tokens": 20, "output_tokens": 10}}


class FakeRetrieval:
    def __init__(self, passages=None):
        self.passages = (
            passages
            if passages is not None
            else [
                {
                    "id": "chunk-1",
                    "source_id": "source-1",
                    "title": "station.md",
                    "text": "The battery holds 40 kWh.",
                    "version": 1,
                    "score": 0.9,
                }
            ]
        )
        self.calls = []
        self.added = {}

    def search(self, query, hybrid=False, k=5):
        self.calls.append((query, hybrid, k))
        return self.passages

    def add(self, documents, ids):
        self.added.update(dict(zip(ids, documents)))

    def delete(self, ids):
        for cid in ids:
            self.added.pop(cid, None)

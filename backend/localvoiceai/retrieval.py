import json
import threading
from functools import cached_property

from fastembed import TextEmbedding
from langchain_core.embeddings import Embeddings
from langchain_qdrant import FastEmbedSparse, QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient, models


class LocalEmbeddings(Embeddings):
    def __init__(self, settings):
        self.settings = settings

    @cached_property
    def engine(self):
        # Use complete local assets without querying Hub metadata on every restart.
        try:
            return TextEmbedding(
                model_name=self.settings.embedding_model,
                cache_dir=str(self.settings.data_dir / "models"),
                local_files_only=True,
            )
        except (OSError, ValueError):
            if self.settings.offline:
                raise
        return TextEmbedding(
            model_name=self.settings.embedding_model,
            cache_dir=str(self.settings.data_dir / "models"),
            local_files_only=self.settings.offline,
        )

    def embed_documents(self, texts):
        return [v.tolist() for v in self.engine.embed(texts)]

    def embed_query(self, text):
        return next(self.engine.query_embed(text)).tolist()


class Retrieval:
    def __init__(self, settings, db):
        self.settings, self.db = settings, db
        self.client = QdrantClient(path=str(settings.data_dir / "qdrant"))
        self.lock = threading.RLock()
        self.collection = "knowledge_v1"
        self.embeddings = LocalEmbeddings(settings)

    @cached_property
    def sparse(self):
        try:
            return FastEmbedSparse(
                model_name="Qdrant/bm25",
                cache_dir=str(self.settings.data_dir / "models"),
                local_files_only=True,
            )
        except (OSError, ValueError):
            if self.settings.offline:
                raise
        return FastEmbedSparse(
            model_name="Qdrant/bm25",
            cache_dir=str(self.settings.data_dir / "models"),
            local_files_only=self.settings.offline,
        )

    def store(self, hybrid=True):
        return QdrantVectorStore(
            client=self.client,
            collection_name=self.collection,
            embedding=self.embeddings,
            sparse_embedding=self.sparse,
            vector_name="dense",
            sparse_vector_name="sparse",
            retrieval_mode=RetrievalMode.HYBRID if hybrid else RetrievalMode.DENSE,
        )

    def ensure(self):
        if not self.client.collection_exists(self.collection):
            size = len(self.embeddings.embed_query("dimension probe"))
            self.client.create_collection(
                self.collection,
                vectors_config={"dense": models.VectorParams(size=size, distance=models.Distance.COSINE)},
                sparse_vectors_config={"sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)},
            )
            (self.settings.data_dir / "embedding.json").write_text(
                json.dumps({"model": self.settings.embedding_model, "dimensions": size}), encoding="utf-8"
            )
        manifest = self.settings.data_dir / "embedding.json"
        if manifest.exists() and json.loads(manifest.read_text())["model"] != self.settings.embedding_model:
            raise ValueError("Embedding model changed. Use a new LVA_DATA_DIR and reimport your sources.")

    def add(self, documents, ids):
        with self.lock:
            self.ensure()
            self.store().add_documents(documents, ids=ids, batch_size=32)

    def delete(self, ids):
        with self.lock:
            if ids and self.client.collection_exists(self.collection):
                self.client.delete(self.collection, points_selector=ids)

    def search(self, query, hybrid=False, k=5):
        with self.lock:
            sources = self.db.rows("SELECT id,version,generation FROM sources WHERE version>0")
            if not sources or not self.client.collection_exists(self.collection):
                return []
            self.ensure()
            # Uncommitted and abandoned refresh vectors can never enter retrieval.
            conditions = []
            for source in sources:
                must = [
                    models.FieldCondition(
                        key="metadata.source_id", match=models.MatchValue(value=source["id"])
                    ),
                    models.FieldCondition(
                        key="metadata.version", match=models.MatchValue(value=source["version"])
                    ),
                ]
                if source["generation"]:
                    must.append(
                        models.FieldCondition(
                            key="metadata.generation", match=models.MatchValue(value=source["generation"])
                        )
                    )
                else:
                    # Earlier development indexes have no generation token: constrain to committed IDs.
                    ids = [
                        c["id"]
                        for c in self.db.rows("SELECT id FROM chunks WHERE source_id=?", (source["id"],))
                    ]
                    if not ids:
                        continue
                    must.append(
                        models.FieldCondition(key="metadata.chunk_id", match=models.MatchAny(any=ids))
                    )
                conditions.append(models.Filter(must=must))
            if not conditions:
                return []
            results = self.store(hybrid).similarity_search_with_score(
                query, k=k, filter=models.Filter(should=conditions)
            )
            return [
                {
                    "id": doc.metadata["chunk_id"],
                    "text": doc.page_content,
                    "score": float(score),
                    **{key: value for key, value in doc.metadata.items() if not key.startswith("_")},
                }
                for doc, score in results
            ]

    def close(self):
        with self.lock:
            self.client.close()

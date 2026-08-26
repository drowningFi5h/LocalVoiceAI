import hashlib
from uuid import uuid4

from conftest import TestEmbeddings
from langchain_core.documents import Document
from langchain_qdrant import SparseEmbeddings, SparseVector
from localvoiceai.db import now
from localvoiceai.retrieval import Retrieval


class TestSparse(SparseEmbeddings):
    __test__ = False

    def embed_documents(self, texts):
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text):
        indices = sorted(
            {int.from_bytes(hashlib.md5(t.encode()).digest()[:2], "big") for t in text.lower().split()}
        )
        return SparseVector(indices=indices, values=[1.0] * len(indices))


def test_qdrant_dense_hybrid_active_versions_delete_and_restart(settings, db):
    retrieval = Retrieval(settings, db)
    retrieval.embeddings = TestEmbeddings()
    retrieval.sparse = TestSparse()
    db.execute(
        "INSERT INTO sources(id,title,kind,version,updated,generation) VALUES (?,?,?,?,?,?)",
        ("source-a", "battery.md", "md", 1, now(), "active"),
    )
    active, orphan, abandoned = str(uuid4()), str(uuid4()), str(uuid4())
    documents = [
        Document(
            page_content="battery solar power",
            metadata={
                "chunk_id": cid,
                "source_id": "source-a",
                "version": version,
                "title": "battery.md",
                "generation": generation,
            },
        )
        for cid, version, generation in [
            (active, 1, "active"),
            (orphan, 2, "replacement"),
            (abandoned, 1, "abandoned-retry"),
        ]
    ]
    retrieval.add(documents, [active, orphan, abandoned])
    for hybrid in [False, True]:
        assert [p["id"] for p in retrieval.search("battery", hybrid)] == [active]
    db.execute("UPDATE sources SET version=2,generation='replacement' WHERE id='source-a'")
    assert [p["id"] for p in retrieval.search("battery", True)] == [orphan]
    retrieval.close()
    reopened = Retrieval(settings, db)
    reopened.embeddings = TestEmbeddings()
    reopened.sparse = TestSparse()
    assert reopened.search("battery")[0]["id"] == orphan
    db.execute("DELETE FROM sources WHERE id='source-a'")
    assert reopened.search("battery", True) == []
    reopened.delete([active, orphan, abandoned])
    assert reopened.client.count(reopened.collection).count == 0
    reopened.close()

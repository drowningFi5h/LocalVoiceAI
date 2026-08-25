import asyncio
import hashlib
import io
import json
import re
from pathlib import Path
from uuid import uuid4

import trafilatura
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from .webfetch import fetch_page


def extract(data: bytes, kind: str, title: str):
    if kind == "pdf":
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are unsupported. Upload an unlocked copy.")
        pages = [
            Document(page_content=page.extract_text() or "", metadata={"page": n + 1})
            for n, page in enumerate(reader.pages)
        ]
        if not any(page.page_content.strip() for page in pages):
            raise ValueError("No extractable text. Scanned PDFs require OCR, which is not included.")
        return [p for p in pages if p.page_content.strip()]
    if kind == "url":
        text = trafilatura.extract(data, include_tables=True, include_links=False)
        if not text:
            raise ValueError(
                "No readable page content. JavaScript-only and authenticated pages are unsupported."
            )
    else:
        text = data.decode("utf-8-sig")
    if not text.strip():
        raise ValueError("The document contains no text.")
    parts = re.split(r"(?m)(?=^#{1,6}\s)", text) if kind == "md" else [text]
    return [
        Document(
            page_content=part,
            metadata={"section": part.splitlines()[0].lstrip("# ")[:160] if kind == "md" else title},
        )
        for part in parts
        if part.strip()
    ]


class Ingestion:
    def __init__(self, settings, db, retrieval):
        self.settings, self.db, self.retrieval = settings, db, retrieval
        self.lock = asyncio.Lock()
        self.tasks = set()

    def schedule(self, source_id):
        task = asyncio.create_task(self.run(source_id))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def run(self, source_id):
        async with self.lock:
            source = self.db.source(source_id)
            if not source:
                return
            ids = []
            committed = False
            try:
                self.db.update_source(source_id, status="indexing", progress=5, error=None)
                url = source["url"]
                if source["kind"] == "url":
                    if self.settings.offline:
                        raise ValueError("Web imports are disabled in offline mode.")
                    data, url, content_type = await fetch_page(url, self.settings.max_page_bytes)
                    kind = "txt" if "text/plain" in content_type else "url"
                else:
                    data = await asyncio.to_thread(Path(source["path"]).read_bytes)
                    kind = source["kind"]
                digest = hashlib.sha256(data).hexdigest()
                duplicate = self.db.one(
                    "SELECT id,title FROM sources WHERE hash=? AND id!=? AND version>0", (digest, source_id)
                )
                if duplicate:
                    raise ValueError(f"Duplicate of {duplicate['title']} ({duplicate['id']}).")
                if digest == source["hash"] and source["version"] and source["generation"]:
                    self.db.update_source(source_id, status="ready", progress=100)
                    return
                docs = await asyncio.to_thread(extract, data, kind, source["title"])
                if self.settings.offline:
                    import os

                    cache = Path(
                        os.environ.get("TIKTOKEN_CACHE_DIR", self.settings.data_dir / "models" / "tiktoken")
                    )
                    key = hashlib.sha1(
                        b"https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"
                    ).hexdigest()
                    if not (cache / key).exists():
                        raise ValueError(
                            "Tokenizer is not cached. Warm models online before enabling offline mode."
                        )
                splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                    encoding_name="cl100k_base", chunk_size=600, chunk_overlap=100
                )
                chunks = await asyncio.to_thread(splitter.split_documents, docs)
                if len(chunks) > 10000:
                    raise ValueError("Document exceeds the 10,000 chunk limit.")
                version = source["version"] + 1
                generation = str(uuid4())
                ids = [str(uuid4()) for _ in chunks]
                for chunk, chunk_id in zip(chunks, ids):
                    chunk.metadata.update(
                        source_id=source_id,
                        chunk_id=chunk_id,
                        version=version,
                        generation=generation,
                        title=source["title"],
                        url=url,
                        content_hash=digest,
                    )
                self.db.update_source(source_id, progress=35)
                await asyncio.to_thread(self.retrieval.add, chunks, ids)
                old = self.db.rows("SELECT id FROM chunks WHERE source_id=?", (source_id,))
                with self.db.lock, self.db.conn:
                    self.db.conn.execute("DELETE FROM chunks WHERE source_id=?", (source_id,))
                    self.db.conn.executemany(
                        "INSERT INTO chunks VALUES (?,?,?,?,?)",
                        [
                            (cid, source_id, version, doc.page_content, json.dumps(doc.metadata))
                            for cid, doc in zip(ids, chunks)
                        ],
                    )
                    self.db.conn.execute(
                        "UPDATE sources SET hash=?,version=?,chunks=?,generation=?,status='ready',"
                        "progress=100,error=NULL WHERE id=?",
                        (digest, version, len(chunks), generation, source_id),
                    )
                committed = True
                await asyncio.to_thread(self.retrieval.delete, [r["id"] for r in old])
            except asyncio.CancelledError:
                self.db.update_source(
                    source_id, status="error", error="Indexing interrupted; refresh to retry."
                )
                raise
            except Exception as exc:
                if not committed:
                    try:
                        await asyncio.to_thread(self.retrieval.delete, ids)
                    except Exception:
                        pass  # Orphans are excluded by the active-version filter.
                    self.db.update_source(source_id, status="error", error=str(exc)[:500])

    async def delete(self, source_id):
        async with self.lock:
            source = self.db.source(source_id)
            if not source:
                return
            ids = [r["id"] for r in self.db.rows("SELECT id FROM chunks WHERE source_id=?", (source_id,))]
            # Remove eligibility first; a failed vector cleanup cannot expose deleted content.
            self.db.execute("DELETE FROM chunks WHERE source_id=?", (source_id,))
            self.db.execute("DELETE FROM sources WHERE id=?", (source_id,))
            await asyncio.to_thread(self.retrieval.delete, ids)
            if source["path"]:
                Path(source["path"]).unlink(missing_ok=True)

import pytest
from conftest import FakeRetrieval
from langchain_text_splitters import RecursiveCharacterTextSplitter
from localvoiceai.db import now
from localvoiceai.ingestion import Ingestion, extract


@pytest.fixture(autouse=True)
def local_tokenizer(monkeypatch):
    # Unit tests must not download tokenizer assets; real tokenization has a separate smoke check.
    monkeypatch.setattr(
        RecursiveCharacterTextSplitter,
        "from_tiktoken_encoder",
        lambda **kw: RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100),
    )


def add_source(db, settings, source_id="one", text="# Battery\nThe battery holds 40 kWh."):
    path = settings.data_dir / "uploads" / f"{source_id}.md"
    path.write_text(text, encoding="utf-8")
    db.execute(
        "INSERT INTO sources(id,title,kind,path,updated) VALUES (?,?,?,?,?)",
        (source_id, "station.md", "md", str(path), now()),
    )
    return path


async def test_index_duplicate_refresh_and_delete(settings, db):
    retrieval = FakeRetrieval()
    jobs = Ingestion(settings, db, retrieval)
    path = add_source(db, settings)
    await jobs.run("one")
    assert db.source("one")["version"] == 1
    assert len(retrieval.added) == 1
    await jobs.run("one")
    assert db.source("one")["version"] == 1
    add_source(db, settings, "two")
    await jobs.run("two")
    assert "Duplicate" in db.source("two")["error"]
    old_ids = set(retrieval.added)
    path.write_text("# Updated\nThe new battery holds 50 kWh.")
    await jobs.run("one")
    assert db.source("one")["version"] == 2
    assert not old_ids & set(retrieval.added)
    assert "50" in db.one("SELECT text FROM chunks WHERE source_id='one'")["text"]
    await jobs.delete("one")
    assert not db.source("one")
    assert not retrieval.added
    assert not path.exists()


async def test_failed_refresh_keeps_previous_index(settings, db, monkeypatch):
    retrieval = FakeRetrieval()
    jobs = Ingestion(settings, db, retrieval)
    path = add_source(db, settings)
    await jobs.run("one")
    old = db.rows("SELECT * FROM chunks")
    path.write_text("Changed document")

    def fail(*args):
        raise RuntimeError("Model unavailable")

    monkeypatch.setattr(retrieval, "add", fail)
    await jobs.run("one")
    assert db.source("one")["status"] == "error"
    assert db.source("one")["version"] == 1
    assert db.rows("SELECT * FROM chunks") == old


def test_empty_documents_and_heading_metadata():
    with pytest.raises(ValueError, match="no text"):
        extract(b"  ", "txt", "Empty")
    docs = extract(b"# One\nFirst section\n# Two\nSecond section", "md", "Notes")
    assert [d.metadata["section"] for d in docs] == ["One", "Two"]


def test_scanned_pdf_message():
    import io

    from pypdf import PdfWriter

    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(output)
    with pytest.raises(ValueError, match="Scanned PDFs"):
        extract(output.getvalue(), "pdf", "scan.pdf")

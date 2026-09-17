import asyncio
import importlib.util
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel, Field

from .config import Settings
from .db import Database, now
from .evaluation import ROOT, Evaluations, summarize
from .graph import Pipeline
from .ingestion import Ingestion
from .models import Models
from .pairing import Pairing
from .providers import PROVIDERS, ProviderInput, provider_name
from .speech import Speech
from .transport import Conversation


class URLInput(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


class EvalInput(BaseModel):
    provider: Literal["local", "cloud"] = "local"


class ReviewInput(BaseModel):
    case_id: str
    mode: Literal["baseline", "graph"]
    answer_correct: bool
    citations_supported: bool


def create_app(settings=None):
    settings = settings or Settings()
    pairing = Pairing(settings.data_dir)
    trusted_origins = [o for o in settings.origins if urlsplit(o).hostname in {"localhost", "127.0.0.1"}]
    allowed_origins = trusted_origins + ([pairing.origin] if pairing.origin else [])
    cloud_defaults = {
        key: getattr(settings, key)
        for key in ("cloud_backend", "cloud_model", "cloud_api_key", "cloud_base_url")
    }
    provider_override = False
    connections = {}
    active_connection = None

    @asynccontextmanager
    async def lifespan(app):
        settings.prepare()
        # Redirect model caches into the application data directory.
        os.environ.setdefault("HF_HOME", str(settings.data_dir.resolve() / "models" / "huggingface"))
        os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(settings.data_dir.resolve() / "models" / "tiktoken"))
        if settings.offline:
            os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        from .retrieval import Retrieval

        db = Database(settings.data_dir / "app.sqlite")
        retrieval = Retrieval(settings, db)
        models = Models(settings)
        async with AsyncSqliteSaver.from_conn_string(str(settings.data_dir / "checkpoints.sqlite")) as saver:
            await saver.setup()
            pipeline = Pipeline(retrieval, models, saver)
            ingestion = Ingestion(settings, db, retrieval)
            evaluations = Evaluations(db, pipeline)
            app.state.s = SimpleNamespace(
                db=db,
                retrieval=retrieval,
                models=models,
                pipeline=pipeline,
                ingestion=ingestion,
                evaluations=evaluations,
                speech=Speech(settings),
                connections=set(),
                conversations={},
            )
            yield
            tasks = list(ingestion.tasks | evaluations.tasks)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        retrieval.close()
        db.close()

    app = FastAPI(title="LocalVoiceAI", version="0.1.0", lifespan=lifespan)
    @app.middleware("http")
    async def local_origin(request: Request, call_next):
        from fastapi.responses import JSONResponse

        origin = request.headers.get("origin")
        if origin and origin not in allowed_origins:
            return JSONResponse({"detail": "Origin is not allowed."}, status_code=403)
        if request.url.hostname not in {"localhost", "127.0.0.1", "testserver"}:
            return JSONResponse({"detail": "Localhost service only."}, status_code=403)
        if origin and origin not in trusted_origins and request.method != "OPTIONS":
            token = request.headers.get("authorization", "").removeprefix("Bearer ")
            if not pairing.authorized(origin, token):
                return JSONResponse({"detail": "Pairing token rejected. Reconnect your local workspace."}, status_code=401)
        return await call_next(request)

    app.add_middleware(CORSMiddleware, allow_origins=allowed_origins,
                       allow_methods=["GET", "POST", "DELETE"],
                       allow_headers=["Content-Type", "Authorization"])

    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "workspace_protocol": 1,
            "local_model": settings.local_model,
            "local_backend": settings.local_backend,
            "cloud_model": settings.cloud_model,
            "cloud_backend": settings.cloud_backend,
            "cloud_provider": provider_name(settings),
            "cloud_override": provider_override,
            "cloud_connection_id": active_connection,
            "cloud_available": bool(settings.cloud_api_key) and not settings.offline,
            "embedding_model": settings.embedding_model,
            "offline": settings.offline,
            "voice_installed": all(
                importlib.util.find_spec(m) for m in ("faster_whisper", "silero_vad", "kokoro")
            ),
        }

    def require_idle():
        s = app.state.s
        if s.evaluations.tasks or any(
            c.voice or (c.task and not c.task.done()) or c.audio_chunks for c in s.conversations.values()
        ):
            raise HTTPException(
                409, "Stop voice, playback, answers and evaluations before changing API settings."
            )

    @app.post("/api/provider")
    async def configure_provider(request: Request):
        nonlocal provider_override, active_connection
        require_idle()
        # Avoid FastAPI validation responses echoing credential inputs.
        try:
            body = ProviderInput.model_validate(await request.json())
        except Exception:
            raise HTTPException(
                422, "Choose a supported provider, model identifier and valid API key."
            ) from None
        require_idle()
        previous = connections.get(body.id)
        if body.id and not previous:
            raise HTTPException(404, "Connection not found.")
        if not body.api_key and (not previous or previous["provider"] != body.provider):
            raise HTTPException(422, "Enter a key for this provider.")
        if not body.id and len(connections) >= 20:
            raise HTTPException(422, "Remove a connection before adding more (maximum 20).")
        _, backend, endpoint = PROVIDERS[body.provider]
        settings.cloud_backend = backend
        settings.cloud_model = body.model
        settings.cloud_base_url = endpoint
        settings.cloud_api_key = body.api_key.get_secret_value() if body.api_key else previous["key"]
        active_connection = body.id or str(uuid4())
        connections[active_connection] = {
            "id": active_connection,
            "name": body.name.strip() or PROVIDERS[body.provider][0],
            "provider": body.provider,
            "model": body.model,
            "key": settings.cloud_api_key,
        }
        provider_override = True
        return await health()

    @app.delete("/api/provider")
    async def restore_provider():
        nonlocal provider_override, active_connection
        require_idle()
        for key, value in cloud_defaults.items():
            setattr(settings, key, value)
        provider_override = False
        active_connection = None
        return await health()

    @app.get("/api/provider/connections")
    async def list_connections():
        return [{k: v for k, v in item.items() if k != "key"} for item in connections.values()]

    @app.post("/api/provider/connections/{connection_id}/activate")
    async def activate_connection(connection_id: str):
        nonlocal provider_override, active_connection
        require_idle()
        item = connections.get(connection_id)
        if not item:
            raise HTTPException(404, "Connection not found.")
        _, settings.cloud_backend, settings.cloud_base_url = PROVIDERS[item["provider"]]
        settings.cloud_model, settings.cloud_api_key = item["model"], item["key"]
        provider_override, active_connection = True, connection_id
        return await health()

    @app.delete("/api/provider/connections/{connection_id}")
    async def delete_connection(connection_id: str):
        require_idle()
        if connection_id not in connections:
            raise HTTPException(404, "Connection not found.")
        if active_connection == connection_id:
            await restore_provider()
        del connections[connection_id]
        return await health()

    @app.get("/api/models/status")
    async def model_status():
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                if settings.local_backend == "lmstudio":
                    headers = (
                        {"Authorization": f"Bearer {settings.lmstudio_api_key}"}
                        if settings.lmstudio_api_key
                        else {}
                    )
                    response = await client.get(settings.lmstudio_url + "/models", headers=headers)
                else:
                    response = await client.get(settings.ollama_url + "/api/tags")
                response.raise_for_status()
                available = (
                    [m["id"] for m in response.json().get("data", [])]
                    if settings.local_backend == "lmstudio"
                    else [m["name"] for m in response.json().get("models", [])]
                )
            return {
                "connected": True,
                "models": available,
                "ready": settings.local_model in available,
                "backend": settings.local_backend,
            }
        except Exception:
            return {"connected": False, "models": [], "ready": False}

    @app.get("/api/sources")
    async def sources():
        return app.state.s.db.rows("SELECT * FROM sources ORDER BY updated DESC")

    @app.get("/api/suggestions")
    async def suggestions(q: str = ""):
        from .suggestions import suggest_sources

        db = app.state.s.db
        sources = db.rows("SELECT id,title FROM sources WHERE version>0")
        chunks = db.rows(
            "SELECT c.source_id,c.text FROM chunks c JOIN sources s ON c.source_id=s.id AND c.version=s.version LIMIT 3000"
        )
        return await asyncio.to_thread(suggest_sources, q[:2000], sources, chunks)

    async def add_upload(filename, data):
        suffix = Path(filename).suffix.lower().lstrip(".")
        if suffix not in {"pdf", "md", "txt"}:
            raise HTTPException(422, "Only PDF, Markdown, and TXT files are supported.")
        if not data or len(data) > settings.max_upload_bytes:
            raise HTTPException(413, "Upload must contain between 1 byte and 20 MB.")
        import hashlib

        duplicate = app.state.s.db.one(
            "SELECT id FROM sources WHERE hash=? AND version>0", (hashlib.sha256(data).hexdigest(),)
        )
        if duplicate:
            return {"id": duplicate["id"], "duplicate": True}
        source_id = str(uuid4())
        path = settings.data_dir.resolve() / "uploads" / f"{source_id}.{suffix}"
        await asyncio.to_thread(path.write_bytes, data)
        title = filename.replace("\\", "/").split("/")[-1][:200]
        app.state.s.db.execute(
            "INSERT INTO sources(id,title,kind,path,updated) VALUES (?,?,?,?,?)",
            (source_id, title, suffix, str(path), now()),
        )
        app.state.s.ingestion.schedule(source_id)
        return {"id": source_id, "duplicate": False}

    @app.post("/api/sources/upload", status_code=202)
    async def upload(file: UploadFile = File(...)):
        try:
            return await add_upload(
                file.filename or "document.txt", await file.read(settings.max_upload_bytes + 1)
            )
        finally:
            await file.close()

    @app.post("/api/sources/url", status_code=202)
    async def url_source(body: URLInput):
        from .webfetch import public_target

        if settings.offline:
            raise HTTPException(422, "Web ingestion is disabled in offline mode.")
        try:
            parsed, _ = await public_target(body.url)
        except (ValueError, OSError) as exc:
            raise HTTPException(422, str(exc)) from exc
        duplicate = app.state.s.db.one("SELECT id FROM sources WHERE url=?", (body.url,))
        if duplicate:
            return {"id": duplicate["id"], "duplicate": True}
        source_id = str(uuid4())
        app.state.s.db.execute(
            "INSERT INTO sources(id,title,kind,url,updated) VALUES (?,?,?,?,?)",
            (source_id, parsed.hostname + parsed.path[:160], "url", body.url, now()),
        )
        app.state.s.ingestion.schedule(source_id)
        return {"id": source_id}

    @app.get("/api/sources/{source_id}")
    async def get_source(source_id: str):
        source = app.state.s.db.source(source_id)
        if not source:
            raise HTTPException(404, "Source not found.")
        chunks = app.state.s.db.rows("SELECT * FROM chunks WHERE source_id=? ORDER BY rowid", (source_id,))
        for chunk in chunks:
            chunk["metadata"] = json.loads(chunk["metadata"])
        return {**source, "passages": chunks}

    @app.post("/api/sources/{source_id}/refresh", status_code=202)
    async def refresh(source_id: str):
        source = app.state.s.db.source(source_id)
        if not source:
            raise HTTPException(404, "Source not found.")
        if source["status"] in {"queued", "indexing"}:
            raise HTTPException(409, "Source is already indexing.")
        app.state.s.db.update_source(source_id, status="queued", progress=0, error=None)
        app.state.s.ingestion.schedule(source_id)
        return {"id": source_id}

    @app.post("/api/sources/{source_id}/replace", status_code=202)
    async def replace(source_id: str, file: UploadFile = File(...)):
        source = app.state.s.db.source(source_id)
        if not source or source["kind"] == "url":
            raise HTTPException(404, "Uploaded source not found.")
        if source["status"] in {"queued", "indexing"}:
            raise HTTPException(409, "Source is already indexing.")
        try:
            data = await file.read(settings.max_upload_bytes + 1)
        finally:
            await file.close()
        if not data or len(data) > settings.max_upload_bytes:
            raise HTTPException(413, "Invalid upload size.")
        if Path(file.filename or "").suffix.lower() != "." + source["kind"]:
            raise HTTPException(422, "Replacement must have the same file type.")
        await asyncio.to_thread(Path(source["path"]).write_bytes, data)
        return await refresh(source_id)

    @app.delete("/api/sources/{source_id}")
    async def delete(source_id: str):
        await app.state.s.ingestion.delete(source_id)
        return {"deleted": source_id}

    @app.post("/api/demo/import", status_code=202)
    async def demo():
        return [
            await add_upload(path.name, path.read_bytes())
            for path in sorted((ROOT / "sample_data" / "documents").glob("*.md"))
        ]

    @app.post("/api/sessions")
    async def session():
        return {"id": app.state.s.db.session()}

    @app.get("/api/sessions/{session_id}")
    async def history(session_id: str):
        if not app.state.s.db.one("SELECT id FROM sessions WHERE id=?", (session_id,)):
            raise HTTPException(404, "Session not found.")
        return app.state.s.db.history(session_id)

    @app.websocket("/api/ws/{session_id}")
    async def websocket(ws: WebSocket, session_id: str):
        s = app.state.s
        if ws.headers.get("origin") not in allowed_origins or ws.url.hostname not in {
            "localhost",
            "127.0.0.1",
        }:
            await ws.close(code=1008)
            return
        origin = ws.headers.get("origin")
        protocols = ws.headers.get("sec-websocket-protocol", "").split(",")
        token = next((p.strip()[9:] for p in protocols if p.strip().startswith("lva-pair.")), "")
        if origin not in trusted_origins and not pairing.authorized(origin, token):
            await ws.close(code=1008)
            return
        if session_id in s.connections or not s.db.one("SELECT id FROM sessions WHERE id=?", (session_id,)):
            await ws.close(code=1008)
            return
        s.connections.add(session_id)
        try:
            conversation = Conversation(ws, session_id, s)
            s.conversations[session_id] = conversation
            await conversation.run()
        finally:
            s.connections.discard(session_id)
            s.conversations.pop(session_id, None)

    @app.post("/api/evaluations", status_code=202)
    async def evaluate(body: EvalInput):
        if app.state.s.evaluations.tasks:
            raise HTTPException(409, "An evaluation is already running.")
        cases = json.loads((ROOT / "sample_data" / "benchmark.json").read_text())
        needed = {title for c in cases for title in c["expected_sources"]}
        ready = {s["title"] for s in app.state.s.db.rows("SELECT title FROM sources WHERE status='ready'")}
        if not needed.issubset(ready):
            raise HTTPException(409, "Import the demo corpus and wait for indexing before evaluating.")
        try:
            app.state.s.models.chat(body.provider)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"id": app.state.s.evaluations.start(body.provider)}

    @app.get("/api/evaluations")
    async def evaluations():
        rows = app.state.s.db.rows("SELECT * FROM evaluations ORDER BY created DESC")
        for row in rows:
            row["result"] = json.loads(row["result"])
        return rows

    @app.post("/api/evaluations/{run_id}/review")
    async def review(run_id: str, body: ReviewInput):
        run = app.state.s.db.one("SELECT * FROM evaluations WHERE id=?", (run_id,))
        if not run:
            raise HTTPException(404, "Evaluation not found.")
        if run["status"] == "running":
            raise HTTPException(409, "Wait for the run to finish before reviewing.")
        result = json.loads(run["result"])
        row = next((r for r in result["rows"] if r["id"] == body.case_id and r["mode"] == body.mode), None)
        if not row or "error" in row:
            raise HTTPException(404, "Completed case not found.")
        row["review"] = {
            "answer_correct": body.answer_correct,
            "citations_supported": body.citations_supported,
        }
        result["summary"] = summarize(result["rows"])
        app.state.s.db.execute("UPDATE evaluations SET result=? WHERE id=?", (json.dumps(result), run_id))
        return result

    dist = ROOT / "frontend" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/audio-worklet.js")
        async def worklet():
            return FileResponse(dist / "audio-worklet.js", media_type="application/javascript")

        @app.get("/")
        async def index():
            return FileResponse(dist / "index.html")

    return app


app = create_app()

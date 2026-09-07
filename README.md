# LocalVoiceAI

An AI voice assistant for working with your documents while keeping local processing under your control.

In Local mode, document storage, search, speech recognition, and answer generation run on your machine. Ask questions aloud, hear the answers, and inspect the passages behind them.

## Features

- Voice and text conversations, with interruptible spoken responses.
- PDF, Markdown, text, and public-page ingestion.
- Cited answers, source previews, and similar-document suggestions.
- Baseline RAG and a LangGraph workflow with a bounded retrieval retry.
- Local generation through LM Studio or Ollama; optional API connections.
- A 40-question benchmark and dashboard for comparing retrieval and answer quality.

## Privacy and control

Local mode doesn't send your questions or document passages to a generation provider. Models need an initial download; after setup, cached models support offline use.

API mode is opt-in and sends questions, recent conversation context, and retrieved passages to the selected provider. Speech and indexing stay local. There is no automatic cloud fallback. Keys entered in the UI stay in server memory and clear on restart.

This is a single-user localhost app, not a hardened document vault. Local files are not encrypted by the application, and it has no authentication layer for public hosting.

## Stack

![React, TypeScript, Vite, Python, FastAPI, and SQLite](https://skillicons.dev/icons?i=react,ts,vite,py,fastapi,sqlite&theme=light)

React · TypeScript · FastAPI · LangChain · LangGraph · Qdrant · SQLite

BGE and BM25 for retrieval. Silero VAD, faster-whisper, and Kokoro for speech.

## Run locally

Requires Python 3.11–3.12, Node.js 22.12+, uv, and a local model server. The PowerShell example below uses Ollama; [SETUP.md](SETUP.md#lm-studio-local-endpoint) covers LM Studio.

```powershell
Copy-Item .env.example .env
uv sync --locked --extra voice
ollama pull qwen3:4b
uv run --extra voice python scripts/warm_models.py --speech
cd frontend
npm ci
npm run build
cd ..
.\scripts\start.ps1
```

Keep Ollama running and open [localhost:8017](http://127.0.0.1:8017). Preserve your existing `.env` if you've already configured the app. Import the Aurora demo corpus to try retrieval without using personal documents.

## Development

```powershell
uv run --extra voice pytest -q
uv run --extra voice ruff check backend tests scripts
cd frontend
npm test
npm run build
```

See [SETUP.md](SETUP.md) for configuration and [VALIDATION.md](VALIDATION.md) for tested behavior and outstanding checks. Benchmark references need human review; model answers and citations can be wrong. Speech is English-only, scanned PDFs need OCR, and live voice latency depends on your hardware.

Component attribution and license details are in [THIRD_PARTY_NOTICES.md](frontend/THIRD_PARTY_NOTICES.md).

# LocalVoiceAI

[Open the hosted studio](https://localvoiceai-pi.vercel.app) · [Setup guide](SETUP.md) · [Connect your local backend](SETUP.md#hosted-frontend-connection)

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

## Where it runs

The website is the frontend. The local Python backend handles documents, RAG, LangGraph, transcription, TTS, and connections to LM Studio or Ollama.

**Using the hosted website still requires the backend on your own computer. Installing LM Studio alone is not enough.** The browser connects directly to that backend; Vercel serves only the interface. Once the page loads, it checks backend connectivity and model readiness separately.

```text
Browser frontend → LocalVoiceAI backend (:8017) → LM Studio (:1234) or Ollama (:11434)
```

Start with the **[local installation and model setup guide](SETUP.md)**, then follow the **[hosted frontend connection guide](SETUP.md#hosted-frontend-connection)** to pair the website with your computer. Keep the backend and model server running. A green checkmark confirms the workspace connection; model readiness is shown separately.

Vercel's [free Hobby plan](https://vercel.com/docs/plans/hobby) can serve this personal portfolio frontend. The backend runs locally, with no cloud hosting bill. Documents and speech stay on your computer; API mode sends generation context to the selected provider. For offline use, open the locally served interface instead.

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

## Models and downloads

Use the official sources below. The warm-up command in the setup guide fetches retrieval and speech assets into the appropriate local caches; generation models are installed separately through LM Studio or Ollama.

| Purpose | Model / download |
|---|---|
| Generation with Ollama | [Qwen3 4B](https://ollama.com/library/qwen3:4b) — `ollama pull qwen3:4b` |
| Generation with LM Studio | [Qwen3-VL-4B-Instruct GGUF](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF) — load a supported quantization and set the model ID returned by your server |
| Document embeddings | [BGE small English v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) |
| Speech recognition | [faster-whisper base.en](https://huggingface.co/Systran/faster-whisper-base.en) |
| Speech synthesis | [Kokoro 82M](https://huggingface.co/hexgrad/Kokoro-82M), with the `af_heart` voice |
| Speech detection | [Silero VAD](https://github.com/snakers4/silero-vad), installed with the speech dependencies |

Download instructions, cache locations, and offline verification are in **[Configuration and model downloads](SETUP.md#configuration-and-model-downloads)**. The generation model does not provide TTS; Kokoro speaks its answers. Model weights are not included in this repository or uploaded to Vercel.

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

## Earlier CLI version

The original CLI and memory implementation remains in `src/` and `configs/`. It is separate from the browser application. The browser workspace uses `backend/` and `frontend/`.

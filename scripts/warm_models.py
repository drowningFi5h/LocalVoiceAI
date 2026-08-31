"""Download model assets explicitly, then run a short local inference check."""

import argparse
import asyncio
import json
import os

from localvoiceai.config import Settings


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--speech", action="store_true", help="Also warm Whisper, Silero, and Kokoro")
    parser.add_argument("--offline", action="store_true", help="Verify cached assets without Hub access")
    args = parser.parse_args()
    settings = Settings()
    if args.offline:
        settings.offline = True
    settings.prepare()
    os.environ.setdefault("HF_HOME", str(settings.data_dir.resolve() / "models" / "huggingface"))
    os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(settings.data_dir.resolve() / "models" / "tiktoken"))
    if settings.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
    import tiktoken
    from langchain_qdrant import FastEmbedSparse
    from localvoiceai.retrieval import LocalEmbeddings

    print("Warming tokenizer, BGE embeddings, and BM25…", flush=True)
    tiktoken.get_encoding("cl100k_base").encode("LocalVoiceAI")
    vector = LocalEmbeddings(settings).embed_query("How is the station powered?")
    sparse = FastEmbedSparse(
        model_name="Qdrant/bm25",
        cache_dir=str(settings.data_dir / "models"),
        local_files_only=settings.offline,
    )
    sparse.embed_query("station power")
    result = {"embedding_model": settings.embedding_model, "dimensions": len(vector), "bm25": "ok"}
    if args.speech:
        import numpy as np
        from localvoiceai.speech import Speech, VoiceDetector

        speech = Speech(settings)
        print("Warming speech models…", flush=True)
        await speech.warm()
        detector = VoiceDetector()
        detector.feed(np.zeros(512, dtype=np.int16).tobytes())
        wav = await asyncio.to_thread(speech.synthesize, "The station uses solar power.")
        (settings.data_dir / "speech-smoke.wav").write_bytes(wav)
        result["speech_wav_bytes"] = len(wav)
        result["silence_transcript"] = speech.transcribe(np.zeros(16000, dtype=np.float32))
    (settings.data_dir / "model-manifest.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())

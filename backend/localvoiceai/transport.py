import asyncio
import base64
import json
import re
import time
from uuid import uuid4

from fastapi import WebSocketDisconnect

from .db import now
from .graph import initial_state
from .speech import VoiceDetector


class Conversation:
    def __init__(self, ws, session_id, services):
        self.ws, self.session_id, self.s = ws, session_id, services
        self.task = None
        self.turn_id = None
        self.detector = None
        self.voice = False
        self.mode, self.provider = "graph", "local"
        self.audio_chunks = {}
        self.send_lock = asyncio.Lock()
        self.speech_ended = None

    async def send(self, event, turn_id=None):
        if turn_id and turn_id != self.turn_id:
            return
        async with self.send_lock:
            await self.ws.send_json({**event, "session_id": self.session_id, "turn_id": turn_id})

    async def cancel(self):
        old = self.turn_id
        interrupted_playback = any(item[0] == old for item in self.audio_chunks.values())
        self.turn_id = None  # Invalidate before awaiting cancellation.
        if self.task and not self.task.done():
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        self.audio_chunks.clear()
        if old:
            self.s.db.execute(
                "UPDATE turns SET status='interrupted' WHERE id=? AND (status='running' OR ?)",
                (old, interrupted_playback),
            )
            await self.send(
                {"type": "cancelled", "cancelled_turn_id": old, "interrupted_playback": interrupted_playback}
            )

    async def start(self, question=None, audio=None):
        await self.cancel()
        self.turn_id = str(uuid4())
        self.task = asyncio.create_task(self.answer(self.turn_id, question, audio))

    async def answer(self, turn_id, question, audio):
        started = time.perf_counter()
        speech_ended = self.speech_ended
        answer = ""
        pending = ""
        audio_worker = None
        saved = False
        queue = asyncio.Queue(maxsize=20)
        mode, provider, voice = self.mode, self.provider, self.voice
        first_audio = None
        try:
            await self.send({"type": "turn_start", "mode": mode, "provider": provider}, turn_id)
            if audio is not None:
                question = await asyncio.to_thread(self.s.speech.transcribe, audio)
                if not question:
                    await self.send({"type": "turn_end", "status": "empty"}, turn_id)
                    return
            await self.send({"type": "transcript", "text": question}, turn_id)
            self.s.db.execute(
                "INSERT INTO turns(id,session_id,question,mode,provider,created) VALUES (?,?,?,?,?,?)",
                (turn_id, self.session_id, question, mode, provider, now()),
            )
            saved = True

            async def synthesize():
                nonlocal first_audio
                while True:
                    sentence = await queue.get()
                    if sentence is None:
                        return
                    try:
                        wav = await asyncio.to_thread(self.s.speech.synthesize, sentence)
                        if turn_id != self.turn_id:
                            return
                        if not wav:
                            continue
                        chunk_id = str(uuid4())
                        self.audio_chunks[chunk_id] = (turn_id, sentence)
                        if first_audio is None:
                            first_audio = round((time.perf_counter() - (speech_ended or started)) * 1000)
                        await self.send(
                            {
                                "type": "audio",
                                "chunk_id": chunk_id,
                                "text": sentence,
                                "wav": base64.b64encode(wav).decode(),
                                "first_audio_ms": first_audio,
                            },
                            turn_id,
                        )
                    except Exception as exc:
                        await self.send(
                            {"type": "warning", "message": "Speech synthesis failed: " + str(exc)[:200]},
                            turn_id,
                        )

            if voice:
                audio_worker = asyncio.create_task(synthesize())

            async def emit(event):
                nonlocal answer, pending
                if event["type"] == "answer_delta":
                    answer += event["text"]
                    self.s.db.execute("UPDATE turns SET answer=? WHERE id=?", (answer, turn_id))
                    if voice:
                        pending += event["text"]
                        # Keep citation markers with the preceding sentence where possible.
                        while match := re.search(r"[.!?](?:\s*\[\d+\])*\s+", pending):
                            await queue.put(pending[: match.end()].strip())
                            pending = pending[match.end() :]
                await self.send(event, turn_id)

            history = [
                {
                    "question": h["question"],
                    "answer": h["answer"],
                    "played": h["played"],
                    "status": h["status"],
                }
                for h in self.s.db.history(self.session_id)
                if h["id"] != turn_id
            ]
            result = await self.s.pipeline.run(
                initial_state(self.session_id, question, mode, provider, history, conversational=True), emit
            )
            await self.send({"type": "citations", "citations": result["citations"]}, turn_id)
            if voice:
                if pending.strip():
                    await queue.put(pending.strip())
                await queue.put(None)
                await audio_worker
            result["trace"]["first_audio_ms"] = first_audio
            self.s.db.execute(
                "UPDATE turns SET answer=?,citations=?,trace=?,status='complete' WHERE id=?",
                (result["answer"], json.dumps(result["citations"]), json.dumps(result["trace"]), turn_id),
            )
            await self.send({"type": "turn_end", "status": "complete", "trace": result["trace"]}, turn_id)
        except asyncio.CancelledError:
            if saved:
                self.s.db.execute(
                    "UPDATE turns SET answer=?,status='interrupted' WHERE id=?", (answer, turn_id)
                )
            raise
        except Exception as exc:
            if saved:
                self.s.db.execute("UPDATE turns SET status='error' WHERE id=?", (turn_id,))
            message = str(exc)
            settings = getattr(getattr(self.s, "models", None), "settings", None)
            for key in (getattr(settings, "cloud_api_key", ""), getattr(settings, "lmstudio_api_key", "")):
                if key:
                    message = message.replace(key, "[redacted]")
            await self.send({"type": "error", "message": "Turn failed: " + message[:400]}, turn_id)
        finally:
            if audio_worker and not audio_worker.done():
                audio_worker.cancel()
                await asyncio.gather(audio_worker, return_exceptions=True)

    async def run(self):
        await self.ws.accept()
        await self.send({"type": "ready"})
        try:
            while True:
                message = await self.ws.receive()
                if message["type"] == "websocket.disconnect":
                    break
                if message.get("bytes") is not None:
                    if not self.voice or self.detector is None:
                        continue
                    pcm = message["bytes"]
                    if len(pcm) != 1024:
                        await self.send({"type": "error", "message": "Invalid audio frame size."})
                        continue
                    began, utterance = await asyncio.to_thread(self.detector.feed, pcm)
                    if began:
                        await self.cancel()
                        await self.send({"type": "speech_start"})
                    if utterance is not None:
                        self.speech_ended = time.perf_counter()
                        await self.start(audio=utterance)
                    continue
                try:
                    event = json.loads(message.get("text") or "{}")
                    if not isinstance(event, dict):
                        raise ValueError("Expected an event object.")
                    kind = event.get("type")
                    if kind in {"configure", "voice_start", "text"}:
                        if event.get("mode", self.mode) not in {"baseline", "graph"}:
                            raise ValueError("Invalid mode.")
                        if event.get("provider", self.provider) not in {"local", "cloud"}:
                            raise ValueError("Invalid provider.")
                        self.mode = event.get("mode", self.mode)
                        self.provider = event.get("provider", self.provider)
                        # Validate cloud selection before sending any private context.
                        if self.provider == "cloud":
                            self.s.models.chat("cloud")
                    if kind == "text":
                        question = event.get("text", "").strip()
                        if not question or len(question) > 8000:
                            raise ValueError("Enter between 1 and 8,000 characters.")
                        self.speech_ended = None
                        await self.start(question=question)
                    elif kind == "cancel":
                        await self.cancel()
                    elif kind == "voice_start":
                        await self.send({"type": "voice_loading"})
                        self.detector = await asyncio.to_thread(VoiceDetector)
                        await self.s.speech.warm()
                        self.voice = True
                        await self.send({"type": "voice_ready"})
                    elif kind == "voice_stop":
                        self.voice = False
                        self.detector = None
                        await self.cancel()
                        await self.send({"type": "voice_stopped"})
                    elif kind == "played":
                        item = self.audio_chunks.pop(event.get("chunk_id"), None)
                        if item and item[0] == event.get("turn_id"):
                            self.s.db.execute(
                                "UPDATE turns SET played=played || ? WHERE id=? AND session_id=?",
                                (item[1] + " ", item[0], self.session_id),
                            )
                except Exception as exc:
                    await self.send({"type": "error", "message": str(exc)[:400]})
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            try:
                await self.cancel()
            except (WebSocketDisconnect, RuntimeError):
                pass

import asyncio
import io
import re
import threading
from collections import deque
from functools import cached_property

import numpy as np


class Speech:
    def __init__(self, settings):
        self.settings = settings
        self.stt_lock = threading.Lock()
        self.tts_lock = threading.Lock()

    @cached_property
    def whisper(self):
        from faster_whisper import WhisperModel

        return WhisperModel(
            self.settings.whisper_model,
            device=self.settings.whisper_device,
            compute_type=self.settings.whisper_compute_type,
            download_root=str(self.settings.data_dir / "models" / "whisper"),
            local_files_only=self.settings.offline,
        )

    @cached_property
    def kokoro(self):
        import spacy
        from kokoro import KPipeline

        if not spacy.util.is_package("en_core_web_sm"):
            raise RuntimeError("English speech assets are missing. Run uv sync --extra voice.")
        return KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cpu")

    def transcribe(self, audio):
        with self.stt_lock:
            segments, _ = self.whisper.transcribe(audio, language="en", beam_size=1, vad_filter=False)
            return " ".join(s.text.strip() for s in segments).strip()

    def synthesize(self, text):
        import soundfile as sf

        # Remove citation markers from speech, retaining them in the displayed answer.
        text = re.sub(r"\[\d+\]", "", text)
        with self.tts_lock:
            chunks = [
                audio.numpy() if hasattr(audio, "numpy") else audio
                for _, _, audio in self.kokoro(text, voice=self.settings.kokoro_voice)
            ]
        if not chunks:
            return b""
        buffer = io.BytesIO()
        sf.write(buffer, np.concatenate(chunks), 24000, format="WAV", subtype="PCM_16")
        return buffer.getvalue()

    async def warm(self):
        def load():
            self.whisper
            self.kokoro.load_voice(self.settings.kokoro_voice)

        await asyncio.to_thread(load)


class VoiceDetector:
    """One Silero state per microphone session, 16 kHz / 512-sample frames."""

    def __init__(self):
        from silero_vad import load_silero_vad

        self.model = load_silero_vad(onnx=True)
        self.reset()

    def reset(self):
        self.model.reset_states()
        self.pre = deque(maxlen=8)
        self.frames = []
        self.active = False
        self.silent = 0

    def feed(self, pcm):
        import torch

        audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768
        if len(audio) != 512:
            raise ValueError("Audio frames must contain 512 mono PCM16 samples at 16 kHz.")
        probability = float(self.model(torch.from_numpy(audio), 16000).item())
        started = False
        if not self.active:
            self.pre.append(audio)
            if probability >= 0.6:
                self.active = started = True
                self.frames = list(self.pre)
                self.pre.clear()
        else:
            self.frames.append(audio)
        if self.active:
            self.silent = self.silent + 1 if probability < 0.35 else 0
            if self.silent >= 18 or len(self.frames) >= 938:  # 576 ms silence / 30-second turn cap
                utterance = np.concatenate(self.frames)
                self.reset()
                return started, utterance
        return started, None

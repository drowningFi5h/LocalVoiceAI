# Validation record — 2026-09-17

## Verified locally

- Python 3.12.14; Node.js 26.3.0.
- `pytest -q`: **30 passed**. One third-party Starlette/AnyIO deprecation warning.
- `ruff check backend tests scripts`: passed.
- `npm test`: **4 passed**.
- `npm run build`: TypeScript checking and Vite production build passed.
- Frontend dependency installation audit: **0 vulnerabilities** after upgrading the build/test tools.
- Real embedded Qdrant dense and hybrid operations, version filtering, deletion, and reopening tested using explicitly deterministic embedding doubles.
- Real SQLite LangGraph checkpoint persisted across reopen; independent session could not read it.
- Baseline and graph branching, retry cap, empty-library abstention, valid citation references, provider failure, source lifecycle, SSRF protection, and interrupted-turn persistence tested.
- Browser AudioWorklet framing verified at 44.1 and 48 kHz input. Stale audio decode and queued-playback cancellation tested.
- Real Silero ONNX model loaded and processed a silence frame successfully.
- Real Kokoro English phoneme conversion succeeded using the pinned spaCy English model. This does not verify synthesis weights or audible output.
- Running UI inspected in the in-app browser. Backend connection, an empty-library question, streamed insufficient-evidence answer, and workflow steps were visibly verified.

## Not yet established

- Hugging Face model downloads failed with remote connection resets after two network-enabled attempts. BGE embedding inference, Whisper transcription, and full Kokoro synthesis were not run successfully with downloaded weights.
- Ollama was not available on the inspected PATH or through the app's configured local-model availability check. No cloud credentials were provided. Actual generation and the 80-answer benchmark remain unverified.
- No claim is made that the ≥85% retrieval or ≥90% abstention targets have been achieved. Answer and citation quality need a real benchmark run and explicit human review.
- Microphone/speaker behavior, echo suppression, acoustic first-audio latency, and the 300 ms interruption target need testing on the user's hardware. Automated tests verify cancellation semantics, not physical audio timing.

## Finish model-backed validation

1. Install/start Ollama and pull `qwen3:4b`, or explicitly configure a cloud model.
2. With Hugging Face reachable, run `uv run --extra voice python scripts/warm_models.py --speech`.
3. Start the app with `scripts/start.ps1` and import the four Aurora documents.
4. Run the benchmark, inspect all errors, and save human reviews for answer correctness and citation support.
5. Use headphones to test interruptions during retrieval, generation, and queued playback. Compare recorded fully-played sentences with what was actually heard.

The application uses port **8017** because port 8000 was already occupied by another local application; that application was left untouched.

## Listening studio UI

The frontend now uses an editorial dark masthead, original animated SVG resonance artwork,
local Manrope/IBM Plex Mono fonts, and a light reading workspace. Anime.js drives the artwork
and entry animation; the primary motion buttons adapt Animate UI's primitive (attribution
and exact upstream license are in frontend/THIRD_PARTY_NOTICES.md and ANIMATE_UI_LICENSE.md).
The artwork can be paused, and animation respects the operating system's reduced-motion setting.
No remote fonts or image services are needed at runtime.

UI verification: production TypeScript/Vite build passed; existing four audio tests passed.
Browser inspection covered desktop (1440px), phone (390px), studio entry, session creation,
library and evaluation navigation. Model readiness is still a separate setup prerequisite.


### Typography and 3D polish — 2026-09-18

Compared all five styles in the four user-supplied archives. Selected Brave Love for
headings and Hathem Bosteem for the short handwritten accent; system sans-serif is used
for reading and controls. Original personal-use font notes are kept with the assets.
The SVG was replaced with an original perspective-projected 3D torus drawn on canvas,
with pointer tilt, a pause control, reduced-motion support, a capped pixel ratio and
a 30fps animation cap. Rendering suspends off-screen and while the tab is hidden.
A prominent Start speaking control invokes the existing voice capture handler.
Build and four audio tests pass; desktop and phone layouts and artwork pause were
inspected in the browser. Live microphone/model inference was not exercised in this UI pass.


### AI Elements voice workspace — 2026-09-18

Applied the supplied design guide: brand-first masthead, concise operational headings,
reduced panel chrome, and a dedicated voice control/transcript workspace. Krylon remains
the display typeface. Integrated an attributed adaptation of AI Elements Transcription
with sentence highlighting synchronized to decoded WAV duration and AudioContext time.
No estimated word timings or unsupported seek behavior are shown. Transcripts are live
client state; durable played-text receipts retain their existing server-side behavior.

Six frontend tests pass, including audio-clock progression, interruption, new-turn isolation,
empty-segment filtering, and active/past transcript states. Production build passes.
Real microphone-to-model-to-speech validation still awaits working model downloads.

### LM Studio connected — 2026-09-18

Configured the local provider at http://localhost:1234/v1 with qwen/qwen3-vl-4b
(Q4_K_M, reported loaded context 16384). A real LangChain streaming request returned
40 kWh [1] with usage metadata in 8.86s. With deterministic evidence fixtures and
real LM Studio generation, baseline and graph workflows both produced the supported
40 kWh answer and one valid citation (3.35s and 5.95s respectively). These are adapter
smoke checks, not corpus retrieval benchmarks or end-to-end speech latency measurements.
The restarted backend reports LM Studio ready and the UI shows the correct local model.
34 backend tests and Ruff checks pass; frontend production build passes. BGE indexing
and the Whisper/Kokoro download and end-to-end checks remain separate outstanding work.

### Local / Gemini switch — 2026-09-18

Added the native LangChain Gemini adapter, server-only credentials, structured
text-block filtering, and provider-key redaction in answer errors. The explicit
Local / API switch coordinates the palette, artwork tint, model labels, and
data-destination disclosure. Active answers/voice sessions lock switching;
local failures do not trigger cloud requests.

37 backend tests, nine frontend tests, Ruff, and the production build pass.
A generic native Google request returned HTTP 200 and `Connected.`. Subsequent
native LangChain streaming checks returned HTTP 503 (model high demand), so
successful Gemini streaming and full cloud RAG are not yet verified. No user
documents were sent by these checks. Local generation verification remains as
documented above.

Browser inspection covered the API theme at 390px and 1440px, animated switching,
provider disclosure, and restoration to Local. The restarted backend reports Gemini
configured. The credential is absent from the built frontend and health response.

### Glass surfaces and user API connections — 2026-09-18

Implemented the supplied image's rounded glass surfaces while retaining the
existing typography, warm Local palette, and blue API palette. The requested
`npx skillfish add fusengine/agents glassmorphism-advanced` ran but reported that
the named skill is absent from that repository. An archived raw copy returned
404; no skill was installed. The design was implemented directly from the image.

39 backend tests and nine frontend tests pass (the initial file-persistence check
was moved after storage closure to avoid a Windows Qdrant lock). Ruff and the
production build pass. New coverage checks all four provider configurations,
credential exclusion from responses and stored files, invalid input without
secret echo, disallowed origins, reset behavior, and active-voice locking.

Browser checks covered desktop Local surfaces and a 390px API layout/dialog.
Saving a dummy key through the UI updated the displayed model and cleared the
input; removing it restored the original Gemini configuration. No inference
request was made with the dummy credential. New provider account access and
live generation remain unverified without the user's respective credentials.

### Panel containment and local model cache — 2026-09-18

Restored inset padding overridden by the older edge-to-edge inspector rules.
Added shrink/wrap constraints for workflow details, evidence titles, and passages;
desktop browser inspection confirms icons, badges, and text stay within cards.

Initial Hub snapshot downloads failed with connection resets. Sequential official
file downloads populated the BGE, BM25, Whisper base.en and Kokoro af_heart caches.
Cache-first loaders now avoid Hub metadata requests when assets are present.
`scripts/warm_models.py --speech --offline` passed: BGE 384 dimensions, BM25 query,
Silero frame processing, Whisper silence transcription, and a 115244-byte Kokoro WAV.
39 backend tests, Ruff and the frontend build pass. This validates local model
loading and inference, not live microphone capture or interruption latency.

### Conversation-first behavior and layout corrections — 2026-09-18

Removed the rounded outer frame while preserving glass surfaces on cards.
Restored source-card padding and title wrapping. Source passage modals explicitly
override the general panel overflow rule so their content scrolls. Browser checks
opened the actual uploaded source and reached the bottom Done control.

Interactive turns now classify intent before choosing conversational generation
or the existing source-grounded pipeline. Conversation uses a warm, curious
LocalVoice persona, conversation history, and no source citations. Ambiguous
classification stays on the source path. Benchmarks retain strict RAG behavior.
42 backend and nine frontend tests pass; Ruff and production build pass.
Live LM Studio checks: a greeting used route → chat without retrieval; summarizing
the uploaded Project Obsidian brief used route → resolve → retrieve → assess →
answer and returned one citation. Classification remains model-dependent.

### Matching suggestions and quieter controls — 2026-09-18

Added local fuzzy title/keyword suggestions and named in-memory API connections
with add, edit, activate, remove, and restore-default controls. No Gemini inference
changes. The provider card is now a model/status strip with on-demand details;
API data destination remains visible. Upload format guidance opens on demand.
44 backend and nine frontend tests pass, plus Ruff and production build.
Browser check: `Obsidan` suggested the uploaded Obsidian brief. Dummy named
connection creation cleared the key field; removal restored the server config.
No inference requests were made with dummy credentials.
